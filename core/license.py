from __future__ import annotations

import json
from pathlib import Path

import config


def get_license_state() -> bool:
    path = Path(config.LICENSE_PATH)
    default = bool(config.DEFAULT_IS_PRO)
    if not path.exists():
        return default

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return bool(payload.get("is_pro", default))
    except Exception:
        return default


def set_license_state(is_pro: bool) -> None:
    path = Path(config.LICENSE_PATH)
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    payload = {"is_pro": bool(is_pro)}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
