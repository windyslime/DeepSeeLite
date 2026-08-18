# Eight-step workflow

All work belongs in `<source-directory>/edit/`; the supplied media stays
unchanged. Read any existing `project.md` first and record the current session.

## 1. 素材檢查

Use `ffprobe` on every source to record streams, duration, dimensions, frame
rate, audio, and readable decode status. Confirm the intended source and
vertical target. Create the adjacent `edit/` workspace only after this check.

## 2. 逐字轉寫

Cache a word-level verbatim transcript under `edit/transcripts/`, keyed to the
unchanged source. ElevenLabs Scribe v2 is the default and required primary path
for this documented full-precision workflow. Before a first upload, obtain the
file-specific consent described in the Skill; do not replace timestamps with
phrase-only subtitles.

If Scribe is unavailable, hand off to setup first. If the user declines cloud
upload or cannot use Scribe, do not silently switch: explain that a local
Whisper fallback has lower-confidence timing, then ask whether the user
explicitly wants it. When chosen, label its transcript lower-confidence and
perform extra boundary playback checks at every EDL edge; never represent its
timing as equal to Scribe.

## 3. 內容整理

Build a readable packed transcript and identify the story, strongest moments,
obvious slips, omissions, likely target length, and ambiguity that needs a
visual check. This is analysis, not an approved cut list.

## 4. 剪輯決策

Give a 4–8 sentence strategy in plain language: audience outcome, narrative
shape, selected material, pacing, estimated duration, visual direction, and
subtitle approach. Wait for approval. Do not independently add B-roll,
animation, music, effects, CTA, or a publishing schedule.

## 5. 逐段粗剪

After approval, build `edl.json` from word-aligned kept ranges. Extract and
process each kept range independently, apply boundary fades, then concatenate.
Apply colour grading or HLG-to-Rec.709 correction only when technically
required or explicitly approved; inspect skin tones in the preview. Inspect
ambiguous cuts with a source timeline view before committing them.

## 6. 轉色／圖卡／字幕

Apply only approved colour changes, cards, or animation. Build simple cards as
static Pillow images. Use HyperFrames only when the approved strategy needs an
HTML, CSS, or GSAP animation and its environment is ready. Generate subtitles
from the EDL on the output timeline and apply them last. Burn subtitles with
the installed Source Han Sans TW font; if it is missing, stop and hand off to
the setup Skill instead of silently substituting another font.

## 7. 混音與完整預覽

Create one complete 720p preview, including the approved mix and visuals.
Check the rendered output at every cut and across its full duration before
showing it as ready for review.

## 8. QA 與正式定稿

Record preview QA evidence, make at most three evidence-led corrections, and
request preview confirmation. After explicit 720p preview approval, render one
1080×1920 formal final, then inspect that final file and run its full decode.
Deliver it only if those final-file checks pass; retain the preview and all
underlying artifacts.
