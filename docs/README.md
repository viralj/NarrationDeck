# Documentation

## Overview
NarrationDeck generates a Resolve timeline from:
- a folder of numbered images (01.png, 02.jpg, etc.)
- narration text (pasted in the GUI)
- audio + SRT (generated from ElevenLabs in later phases)

## Default Workflow (Target)
1) Pick an image folder.
2) Paste narration text.
3) Choose a voice and TTS settings (speed/volume).
4) Generate audio + SRT.
5) Export a Resolve payload JSON.
6) Run the Resolve script to build a project + timeline (images, audio, Text+).

## Using Existing Audio/Timestamps
If you already have audio + timestamps JSON, enable **Use existing artifacts**
in the GUI to skip the ElevenLabs call.

## Shotcut Export
If Resolve scripting is unavailable, you can export a Shotcut `.mlt` project and
open it in Shotcut. Subtitles can be imported from SRT in Shotcut. citeturn0search2turn0search31

## Image Timing Strategy
The planned flow is:
- captions (Text+) are timed strictly to narration SRT timestamps
- image clips are timed by a mapping input like:

```
Image 01 : first words of the segment
Image 02 : next words of the segment
```

Each image starts at the first matching SRT segment and ends at the next image
start. This allows an image to stay on screen during narration pauses while
captions stay hidden outside spoken segments.

In Phase 2, the mapping is resolved against ElevenLabs timestamps and saved as
`*_image_timeline.json`.

### Strict vs Lenient Anchors
By default, NarrationDeck requires every `Image XX : snippet` to match the
generated timestamps. You can enable a lenient mode in the GUI to allow missing
anchors; any unmatched images will be listed in the output log and JSON.
