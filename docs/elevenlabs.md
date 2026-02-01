# ElevenLabs Setup

1) Copy `.env.example` to `.env`.
2) Set your API key:

```
ELEVENLABS_API_KEY=your_key_here
```

3) Update `voices.json` to add or modify voice entries.

Each voice entry includes:
- `label` (human-friendly name)
- `voice_id` (ElevenLabs voice ID)
- `model_id` (ElevenLabs model)

## Output Files
When you click **Generate Audio + SRT**, NarrationDeck will save:
- `narration_YYYYMMDD_HHMMSS.mp3`
- `narration_YYYYMMDD_HHMMSS.srt`
- `narration_YYYYMMDD_HHMMSS_timestamps.json`
- `narration_YYYYMMDD_HHMMSS_image_timeline.json` (if image anchors provided)

These files are saved into the selected images folder.

## Image Anchor Matching
Anchor matching is strict by default; all `Image XX : snippet` entries must be
found in the narration. Enable **Allow missing image anchors (lenient)** in the
GUI to skip unmatched anchors and still generate output.

## Speed Control
ElevenLabs `speed` is clamped to the supported range (0.7 to 1.2).

## Caption Chunking
You can tune caption chunking in the GUI:
- Max characters per caption
- Max caption duration (seconds)
- Line width (characters per line)

Disable **Enable caption chunking limits** to let captions flow with the audio
timestamps without enforcing max duration/length.

## Using Existing Artifacts
If you already generated audio + timestamps, enable **Use existing artifacts**
and select:
- an audio file
- a timestamps JSON file
- optional SRT file

NarrationDeck will skip the API call and build the image timeline from the
timestamps file.
