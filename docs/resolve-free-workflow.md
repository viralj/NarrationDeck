# Resolve Free Workflow (Phase 3)

Resolve Free does not allow external scripting, so NarrationDeck uses a two-step
process:

1) Generate audio + SRT and an image timeline from the GUI.
2) Export a `narrationdeck_payload_*.json` file.
3) Run the Resolve-side script from the **Scripts** menu to build the timeline.

## Install the Resolve Script (Windows)
Copy this script into your Resolve scripts folder:

```
resolve_scripts/narrationdeck_build.py
```

Common locations:
- `%PROGRAMDATA%\Blackmagic Design\DaVinci Resolve\Fusion\Scripts\Comp`
- `%APPDATA%\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Comp`

## Specifying the Payload File

The script uses three methods to find your payload file (in order):

### Method 1: Environment Variable
Set `NARRATIONDECK_PAYLOAD` before launching Resolve:
```powershell
$env:NARRATIONDECK_PAYLOAD = "C:\path\to\narrationdeck_payload_20260131_120000.json"
```

### Method 2: Config File (Recommended for Resolve 20.x)
Create a text file at one of these locations:
- `%USERPROFILE%\Documents\narrationdeck_payload.txt`
- `%USERPROFILE%\narrationdeck_payload.txt`

Put the full path to your payload JSON on the first line:
```
C:\Users\YourName\projects\narrationdeck_payload_20260131_120000.json
```

### Method 3: File Dialog
If neither of the above are set, the script tries to open a file dialog.
**Note:** This may not work in Resolve 20.x due to Python environment restrictions.

## Run the Script
1) Open Resolve.
2) Set up your payload file using Method 1 or 2 above.
3) Go to **Workspace → Scripts** and run `narrationdeck_build.py`.
4) Check the console output for debug messages.

The script will:
- Create or open the target project.
- Create a timeline.
- Import images + audio.
- Place images according to the image timeline JSON.
- Insert Text+ captions using ElevenLabs timestamps (best effort).
  - If Text+ fails, it imports the SRT and prints a manual insert hint.

## Transitions and Fades
Crossfades between images and Text+ fade in/out are not exposed in the Resolve
scripting API for the Free workflow, so they are not automated yet. You can
apply the default transition manually after import.

### Studio Note
If you are on Resolve Studio and can run external scripts, you can still use the
same workflow. For now, apply transitions manually:
- Select all image cuts on the timeline.
- Apply the default video transition (cross dissolve).
- For Text+, apply fade in/out in the Inspector or add keyframes in Fusion.

## Notes
- Text+ insertion depends on the preset name and may fall back to default
  duration if the API refuses to set clip duration.
- If Text+ fails, right-click the SRT clip in the Media Pool and choose
  **Insert Selected Subtitles to Timeline Using Timecode**.
- If a still image duration looks wrong, adjust the Resolve default still
  duration or report the issue so we can refine the placement logic.
