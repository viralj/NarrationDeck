from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

import tkinter as tk

from .gui import NarrationDeckGUI


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _load_voices(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    voices = data.get("voices", [])
    if isinstance(voices, list):
        return [v for v in voices if isinstance(v, dict)]
    return []


def main() -> None:
    root = tk.Tk()
    root.title("NarrationDeck")

    voices_path = _repo_root() / "voices.json"
    voices = _load_voices(voices_path)

    app = NarrationDeckGUI(root, voices=voices)
    app.render()

    root.mainloop()


if __name__ == "__main__":
    main()
