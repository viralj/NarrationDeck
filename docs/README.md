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
5) Build a Resolve project + timeline.

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
