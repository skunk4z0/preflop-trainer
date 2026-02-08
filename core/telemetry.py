# core/telemetry.py
from __future__ import annotations

import json
import re
import time
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


SCHEMA_VERSION = 1


def iso_now() -> str:
    # ローカルTZ（+09:00）でISO8601
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def get_or_create_user_id(data_dir: Path) -> str:
    """
    端末ローカルの匿名ID。
    - data/user_id.txt があればそれを使う
    - 無ければ生成して保存
    """
    data_dir.mkdir(parents=True, exist_ok=True)
    p = data_dir / "user_id.txt"
    if p.exists():
        v = p.read_text(encoding="utf-8").strip()
        if v:
            return v

    v = uuid.uuid4().hex  # 32hex
    p.write_text(v, encoding="utf-8")
    return v


def new_session_id() -> str:
    return uuid.uuid4().hex


def _norm_upper(s: Any) -> str:
    return str(s or "").strip().upper()


def _norm_kind(engine: Any, ctx: Any, answer_mode: str, problem_type: str) -> str:
    """
    kind は「分析/表示で使うレンジ種別」に寄せる。
    優先順位：
      1) ctx.kind が “レンジ種別っぽい”ならそれ
      2) answer_mode（OR_SB / 3BET 等） ← これが最重要
      3) engine.kind があればそれ
      4) problem_type（最後の保険）
    """
    ctx_kind = _norm_upper(getattr(ctx, "kind", None))
    ans = _norm_upper(answer_mode)
    eng_kind = _norm_upper(getattr(engine, "kind", None))
    ptype = _norm_upper(problem_type)

    # ctx.kind が "JUEGO_..." みたいな問題タイプなら採用しない
    if ctx_kind and not ctx_kind.startswith("JUEGO_"):
        return ctx_kind

    if ans:
        return ans

    if eng_kind and not eng_kind.startswith("JUEGO_"):
        return eng_kind

    # 最後は問題タイプ名（ログが空になるよりマシ）
    return ptype or "UNKNOWN"


def _norm_position(pos: Any) -> str:
    """
    position を集計しやすい形に正規化：
    - 大文字
    - 空白/記号を "_" に寄せる
    - 連続 "_" は1個に圧縮
    例: "BB VS CO" -> "BB_VS_CO"
    """
    s = _norm_upper(pos)
    if not s:
        return ""
    # よくある区切りを "_" に
    s = s.replace(" ", "_").replace("-", "_").replace("/", "_")
    # その他の記号も "_" に寄せる
    s = re.sub(r"[^A-Z0-9_]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s


def _norm_hand_key(hk: Any) -> str:
    return _norm_upper(hk)


@dataclass(frozen=True)
class ProblemKey:
    kind: str
    position: str
    hand_key: str
    difficulty: str
    problem_type: str
    answer_mode: str = ""


@dataclass(frozen=True)
class Event:
    schema_version: int
    ts: str
    event_type: str
    user_id: str
    session_id: str
    payload: Dict[str, Any]


class JsonlEventSink:
    """
    1行1JSON（JSONL）で追記。
    """
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, event: Event) -> None:
        line = json.dumps(asdict(event), ensure_ascii=False, separators=(",", ":"))
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(line + "\n")


def build_problem_key(engine: Any, ctx: Any, answer_mode: str = "") -> ProblemKey:
    position_raw = getattr(ctx, "position", "") or ""
    hand_key_raw = getattr(ctx, "excel_hand_key", None) or getattr(ctx, "hand_key", None) or ""

    difficulty = getattr(engine, "difficulty", None)
    difficulty_s = getattr(difficulty, "name", None) or str(difficulty) or ""

    problem_type = getattr(getattr(engine, "current_problem", None), "name", None) or str(getattr(engine, "current_problem", "")) or ""
    problem_type_u = _norm_upper(problem_type)

    answer_mode_u = _norm_upper(answer_mode)
    kind_u = _norm_kind(engine=engine, ctx=ctx, answer_mode=answer_mode_u, problem_type=problem_type_u)

    return ProblemKey(
        kind=kind_u,
        position=_norm_position(position_raw),
        hand_key=_norm_hand_key(hand_key_raw),
        difficulty=_norm_upper(difficulty_s),
        problem_type=problem_type_u,
        answer_mode=answer_mode_u,
    )


def make_question_shown_event(user_id: str, session_id: str, pk: ProblemKey, header_text: str = "") -> Event:
    return Event(
        schema_version=SCHEMA_VERSION,
        ts=iso_now(),
        event_type="question_shown",
        user_id=user_id,
        session_id=session_id,
        payload={
            "problem": asdict(pk),
            "header_text": header_text,
        },
    )


def make_answer_submitted_event(
    user_id: str,
    session_id: str,
    pk: ProblemKey,
    user_action: str,
    expected_action: str,
    correct: Optional[bool],
    response_ms: Optional[int],
    followup_shown: bool,
) -> Event:
    return Event(
        schema_version=SCHEMA_VERSION,
        ts=iso_now(),
        event_type="answer_submitted",
        user_id=user_id,
        session_id=session_id,
        payload={
            "problem": asdict(pk),
            "user_action": _norm_upper(user_action),
            "expected_action": _norm_upper(expected_action),
            "correct": correct,
            "response_ms": response_ms,
            "followup_shown": bool(followup_shown),
        },
    )


def default_data_dir(project_root: Path | None = None) -> Path:
    """
    既定の data ディレクトリ解決。
    - project_root 指定がなければ、このファイルの1つ上(coreの親)をプロジェクトルート扱い
    """
    if project_root is None:
        # core/telemetry.py -> core -> project root
        project_root = Path(__file__).resolve().parent.parent
    return project_root / "data"


def default_events_path(project_root: Path | None = None) -> Path:
    return default_data_dir(project_root) / "events.jsonl"


class Telemetry:
    """
    Controller側から雑に呼べる薄いラッパー。
    """
    def __init__(self, project_root: Path | None = None) -> None:
        self.data_dir = default_data_dir(project_root)
        self.user_id = get_or_create_user_id(self.data_dir)
        self.session_id = new_session_id()
        self.sink = JsonlEventSink(default_events_path(project_root))

        # 直近問題
        self._last_problem_key: Optional[ProblemKey] = None
        self._q_started_at: Optional[float] = None  # perf_counter

    def on_question_shown(self, engine: Any, ctx: Any, answer_mode: str = "", header_text: str = "") -> None:
        pk = build_problem_key(engine, ctx, answer_mode=answer_mode)
        self._last_problem_key = pk
        self._q_started_at = time.perf_counter()
        ev = make_question_shown_event(self.user_id, self.session_id, pk, header_text=header_text)
        self.sink.append(ev)

    def on_answer_submitted(self, engine: Any, ctx: Any, answer_mode: str, user_action: str, res: Any) -> None:
        # pk を確定（直近があればそれを優先）
        pk = self._last_problem_key or build_problem_key(engine, ctx, answer_mode=answer_mode)

        # 直近pkが answer_mode 空のまま残っている場合、今回渡された answer_mode で補正
        if (not pk.answer_mode) and answer_mode:
            pk = build_problem_key(engine, ctx, answer_mode=answer_mode)

        # expected_action の推定（あなたのdebug構造に寄せる）
        expected_action = ""
        jr = getattr(res, "judge_result", None)
        if jr is not None:
            dbg = getattr(jr, "debug", None) or {}
            expected_action = dbg.get("correct_action") or dbg.get("expected_action") or expected_action

        # correct の推定
        correct = getattr(res, "is_correct", None)
        if correct is None and jr is not None:
            correct = getattr(jr, "correct", None)

        # response_ms
        response_ms = None
        if self._q_started_at is not None:
            response_ms = int((time.perf_counter() - self._q_started_at) * 1000)

        followup_shown = bool(getattr(res, "show_followup_buttons", False))

        ev = make_answer_submitted_event(
            self.user_id,
            self.session_id,
            pk,
            user_action=user_action or "",
            expected_action=expected_action or "",
            correct=correct,
            response_ms=response_ms,
            followup_shown=followup_shown,
        )
        self.sink.append(ev)
