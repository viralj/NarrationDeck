# NarrationDeck

Automate DaVinci Resolve (Free) projects from narration text, images, and audio.

This repo is organized in phases. Phase 1 provides a minimal Tkinter GUI and
project scaffolding. Phase 2 adds ElevenLabs TTS (audio + SRT generation).
Later phases add Resolve scripting, timeline assembly, and captions.

## Requirements
- Windows 10/11
- Python 3.10+
- DaVinci Resolve (Free)

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

## Project Structure
- `src/narrationdeck/` - application code
- `voices.json` - selectable voices for ElevenLabs
- `.env` - local secrets (ignored by git)
- `docs/` - setup and usage notes

## Docs
- `docs/README.md` - overview and workflow
- `docs/textplus-preset.md` - Text+ preset setup (Fusion Titles default)
- `docs/elevenlabs.md` - ElevenLabs configuration

## Notes on Resolve Scripting
Later phases will require the Resolve scripting API. If Resolve is installed,
its scripting modules can be added to `PYTHONPATH` or copied into this repo.
We will document the exact steps in Phase 2 when the integration begins.
