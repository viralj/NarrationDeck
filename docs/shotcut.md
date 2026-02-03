# Shotcut Export (MLT)

NarrationDeck can export a Shotcut-compatible `.mlt` project file. Open the
`.mlt` in Shotcut to load the timeline with images + audio. Shotcut supports
importing subtitles from SRT, and NarrationDeck can also embed subtitles in the
MLT export as a best-effort text track. citeturn0search2turn0search31

## Export from NarrationDeck
1) Generate audio/timestamps and image timeline.
2) Click **Export Shotcut MLT**.
3) Open the generated `.mlt` file in Shotcut.

## Import Subtitles (SRT)
1) Open **View → Subtitles** in Shotcut.
2) Import the SRT file (SRT is supported).
3) Make sure the timeline cursor is at 00:00 before importing (Shotcut inserts
   subtitles at the current cursor position). citeturn0search2turn0search31

## Notes
- This export is best-effort and focuses on placing still images and audio.
- For transitions and subtitle styling, use Shotcut tools after import.
- Shotcut uses MLT XML; extra metadata may be added in future exports. citeturn0search1

## Crossfades
If **Shotcut crossfade** is enabled in the GUI, NarrationDeck overlaps images by
the requested duration. This can slightly shift image timing earlier to create
the overlap, so use it only if you are okay with that tradeoff.
