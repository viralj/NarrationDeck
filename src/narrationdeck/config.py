from __future__ import annotations

import json
import os
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _load_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    data: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key.strip()] = value.strip()
    return data


def get_api_key() -> str:
    if os.getenv("ELEVENLABS_API_KEY"):
        return os.getenv("ELEVENLABS_API_KEY", "").strip()
    env_path = _repo_root() / ".env"
    values = _load_env_file(env_path)
    return values.get("ELEVENLABS_API_KEY", "").strip()


def _settings_path() -> Path:
    return _repo_root() / "narrationdeck.settings.json"


def _load_settings() -> dict:
    path = _settings_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def get_setting(key: str, default: str = "") -> str:
    return str(_load_settings().get(key, default))


def set_setting(key: str, value: str) -> None:
    settings = _load_settings()
    settings[key] = value
    _settings_path().write_text(json.dumps(settings, indent=2), encoding="utf-8")
