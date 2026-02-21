import config
from core.license import get_license_state, set_license_state


def test_get_license_state_falls_back_to_default_when_missing(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "LICENSE_PATH", (tmp_path / "license.json").resolve())
    monkeypatch.setattr(config, "DEFAULT_IS_PRO", False)
    assert get_license_state() is False

    monkeypatch.setattr(config, "DEFAULT_IS_PRO", True)
    assert get_license_state() is True


def test_set_and_get_license_state_roundtrip(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "LICENSE_PATH", (tmp_path / "license.json").resolve())
    monkeypatch.setattr(config, "DEFAULT_IS_PRO", False)

    set_license_state(True)
    assert get_license_state() is True

    set_license_state(False)
    assert get_license_state() is False


def test_get_license_state_broken_json_falls_back_to_default(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    path = (tmp_path / "license.json").resolve()
    monkeypatch.setattr(config, "LICENSE_PATH", path)
    monkeypatch.setattr(config, "DEFAULT_IS_PRO", True)

    tmp_path.mkdir(parents=True, exist_ok=True)
    path.write_text("{bad json", encoding="utf-8")
    assert get_license_state() is True
