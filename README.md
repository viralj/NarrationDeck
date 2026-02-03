# NarrationDeck

Automate DaVinci Resolve (Free) projects from narration text, images, and audio.

This repo is organized in phases. Phase 1 provides a minimal Tkinter GUI and
project scaffolding. Phase 2 adds ElevenLabs TTS (audio + SRT generation).
Phase 3 adds a Resolve Free workflow (payload + script). Phase 4 adds Text+
caption insertion (best effort) inside Resolve.

## Requirements
- Windows/macOS/Linux
- Python 3.10+
- DaVinci Resolve (Free or Studio)

Tkinter ships with standard Python on Windows, so no extra GUI dependencies are
required.

## Quick Start (Phase 1)
1) Create a virtual environment (optional).

### Option A: venv
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### Option B: conda/miniconda
```powershell
conda create -n narrationdeck python=3.11
conda activate narrationdeck
```

2) Install the package in editable mode:

```powershell
pip install -e .
```

3) Copy `.env.example` to `.env` and add your ElevenLabs key.
4) Run the GUI:

```powershell
python -m narrationdeck
```

## Quick Flow (Resolve Free)
1) Select your images folder and paste narration text.
2) Generate audio + SRT.
3) Export Resolve payload JSON.
4) Run `resolve_scripts/narrationdeck_build.py` from Resolve **Workspace → Scripts**.

## Project Structure
- `src/narrationdeck/` - application code
- `voices.json` - selectable voices for ElevenLabs
- `.env` - local secrets (ignored by git)
- `docs/` - setup and usage notes

## Docs
- `docs/README.md` - overview and workflow
- `docs/textplus-preset.md` - Text+ preset setup (Fusion Titles default)
- `docs/elevenlabs.md` - ElevenLabs configuration
- `docs/resolve-free-workflow.md` - Resolve Free workflow (payload + script)
- `docs/roadmap.md` - backlog (Free vs Studio items, recommendations)
- `docs/shotcut.md` - Shotcut MLT export workflow

## Notes on Resolve Scripting
Resolve Free does not allow external scripting, so NarrationDeck uses a
payload + in-Resolve script workflow. Studio can run external scripts.
See `docs/resolve-free-workflow.md` for the Free-tier workflow.

### Resolve Free vs Studio
- **Free:** run `resolve_scripts/narrationdeck_build.py` from Resolve's Scripts menu.
- **Studio:** external scripting is supported (future phase will wire the GUI
  directly to Resolve).

### Transitions and Fades
Crossfades and Text+ fades are not automated yet. After import, you can select
all cuts and apply Resolve's default transition, and add Text+ fades in the
Inspector or Fusion as needed.

### Resolve Version Notes
Resolve 20.x introduced changes in scripting behavior and may restrict external
scripts to Studio only. If you are on an older version and external scripts work
in Free, the GUI integration may still work, but this repo targets Free 20.x
with the in-Resolve script workflow.
