from __future__ import annotations

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
