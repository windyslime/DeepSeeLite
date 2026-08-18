# Production rules

## Transcript and edit decisions

- Use word-level verbatim timestamps and cache them per unchanged source. Do
  not re-transcribe unless the source itself changes.
- Snap every edit edge to a word boundary: never cut inside a word. Retain
  30–200ms of boundary padding, selecting the amount from the spoken cadence.
- Store source, start, end, beat, quote, and reason in `edl.json`. Keep its
  source ranges and output offsets internally consistent.
- Extract, process, and verify each kept segment before concatenation. At every
  segment audio edge use about 30ms fades to avoid clicks or pops.

## Visuals, captions, and sound

- Per-segment extraction and processing are mandatory. Apply a colour grade or
  HLG-to-Rec.709 correction only when technically required or explicitly
  approved; inspect skin tones and the resulting image in the preview. Do not
  imply that an unrequested grade is corrective or desired.
- Make simple title and information cards as static Pillow assets. HyperFrames
  is optional and only follows an approved HTML, CSS, or GSAP animation plan.
- Build `master.srt` using output-timeline offsets:
  `output_time = word.start - segment_start + segment_offset`.
- Burn subtitles with the installed Source Han Sans TW font. If the font is
  missing or fails verification, stop and hand off to the setup Skill; do not
  silently substitute another font or accept missing-glyph boxes.
- Apply subtitles last, after all overlays and cards, so they remain visible.
- Keep source audio intelligible; preserve approved music and effects only.

## Preview, QA, and retry limit

1. Render one complete 720p preview before any final export.
2. Inspect the rendered preview at each cut boundary in a ±1.5s window for
   visual jumps, flashes, audio pops, sync, subtitle visibility, and overlay
   alignment. Also inspect first, last, and representative mid-point samples.
3. Perform a full decode check on the preview and record observed duration,
   dimensions, audio, and video streams. Check subtitle safe area, colour
   consistency, and mix.
4. A failed check may trigger a self-fix only when the evidence identifies the
   problem. Limit this loop to three passes; then stop and report remaining
   issues instead of claiming success.
5. After explicit 720p preview approval, render one 1080×1920 formal final.
   Then inspect that final file at its cut boundaries and samples, run a full
   decode, and record its streams, duration, sync, subtitles, colour, and mix.
   Deliver only when these final-file checks pass; do not claim a deliverable
   exists until that file has been rendered and inspected.
