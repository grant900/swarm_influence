# Hackathon video: status and handoff

> **Superseded (2026-10-08).** The video was finished after this note was written: `swarm_video.mp4` (= `video/final.mp4`, sources in `video/`). The audio generators were copied from the scratchpad into `video/audio_src/`, and their output now goes to `video/audio/`. A second cut is in `video_replica/`. Current build steps are in `README.md` → Videos. The rest of this file describes the earlier state; the scratchpad paths it gives may no longer exist.

Goal: a video of 3:00 or less presenting `report.ipynb`. The first ~52 s is the user's recorded intro (`/Users/grantf/Documents/intro.m4a`, 51.56 s), followed by the results.

All working files are in the Claude session scratchpad:

```
SCRATCH=/private/tmp/claude-501/-Users-grantf-repos-swarm-hackathon/058dc6c7-c5ea-4f4c-a060-7fe7539f7f26/scratchpad/video
```

**`/private/tmp` can be cleared on reboot.** Copy `$SCRATCH/audio/` and `$SCRATCH/audio_src/` somewhere durable if you want to keep them.

## Done

### 1. Intro transcription
- `$SCRATCH/intro_transcript.json`: mlx-whisper (large-v3-turbo) output with segment and word-level timestamps. Use it for captions and for syncing visuals to the voice.
- `$SCRATCH/intro16k.wav`: 16 kHz mono copy that was used for transcription.
- The voice runs from 0.0 to 50.9 s. Its last line ("Releasing a swarm and having it ask nicely for these secrets will be enough.") is spoken from 47.6 to 50.9 s.

### 2. Music and sound effects
All files are synthesized locally with numpy/scipy, so there are no third-party assets or licensing questions. Format is 48 kHz, 16-bit, stereo.

`$SCRATCH/audio/music.wav` is 176.0 s and peaks at -3 dBFS. It has four sections:

| Time (s) | Section | Notes |
|---|---|---|
| 0–52 | Under the intro voiceover | Dark pad with a quiet heartbeat. The voice band (300 Hz–4 kHz) is cleared to about -41 to -45 dBFS. It builds from 35 to 47 s. A riser runs from 47.5 to 51.8 s, then there is a ~100 ms gap and a deep impact at **52.0 s**. |
| 53–95 | Case-study section | 100 BPM pulse, clock ticks and a soft minor arpeggio. Intensity rises from 80 to 92 s. |
| 95–152 | Results section | Fuller arrangement with bass and claps. Pad-only dropout from 128 to 130 s, with a soft hit back in at 130 s. |
| 152–176 | Closing | Pad and sparse bells. Cosine fade to silence from 170 to 176 s. |

The sound effects are in `$SCRATCH/audio/`. Each starts at t=0, peaks at -6 dBFS and is meant to be placed with ffmpeg `adelay`:
- `sfx_whoosh.wav`
- `sfx_impact.wav`
- `sfx_type.wav`
- `sfx_typing_burst.wav`
- `sfx_blip.wav`
- `sfx_alert.wav`
- `sfx_stamp.wav`
- `sfx_riser.wav`
- `sfx_data.wav`
- `sfx_tick.wav`
- `sfx_glitch.wav`

Generators are in `$SCRATCH/audio_src/` (`dsp.py`, `music.py`, `sfx.py`, `check.py`). Regenerate with `uv run --with numpy --with scipy python music.py` (same for `sfx.py`).

### 3. Audio review by a second subagent, and the fixes applied
The reviewer passed formats, levels, clicks, impact timing and the overall structure. Its six ranked issues were then fixed in the generators and the audio was regenerated. The pre-fix version is in `$SCRATCH/audio_v1_backup/`, including `music.py.orig` and `sfx.py.orig`.

| Issue from the review | Fix | Before → after |
|---|---|---|
| Riser masked the last spoken line (47.6–50.9 s) | Riser noise lowered and low-passed at 8 kHz. Voice-band clearance added to the fx bus and deepened on the bed. | voice band -17.6 → **-29.8 dBFS** |
| Impact hit weakly: no gap before 52.0 s | Riser and its reverb gated out by 51.9 s. The bed dips from 51.6 to 52.0 s. | level just before the hit -11.1 → **-23.6 dBFS** (impact -8.3) |
| 128–130 s "dropout" carried a hissy noise swell | Swell removed, so the dropout is pad only | >12 kHz energy -39 → **-61 dBFS** |
| `sfx_blip` and `sfx_tick` comb-filter on mono (phones) | L/R delay removed, and from `sfx_type` too | mono-fold loss -8.1 / -6.8 dB → **-0.2 / 0.0 dB** |
| Riser ends abruptly, possible tick | 25 ms end fade in music and in `sfx_riser` | last sample 0.013 → 0.0008 |
| Closing section weak in mono | Side channel narrowed to 55% from 150 to 153 s onward | L/R correlation 0.10 → **0.61**, mono loss -2.6 → -1.0 dB |

Not changed: `sfx_riser` is quiet for its first ~1 s. That is normal for a riser and was flagged only as a deviation from the spec's "starts with sound at t=0".

The script that checks these numbers is `$SCRATCH/audio_fixcheck/verify.py`. The reviewer's own measurements are in `$SCRATCH/audio_review/`.

### 4. Rendering setup (tested and working)
- Playwright (`uv run --with playwright`) drives the installed Google Chrome with `channel="chrome"`. It takes about 0.13 s per 1920×1080 screenshot.
- Fonts are stored locally in `$SCRATCH/web/fonts/`: Inter 400–900, JetBrains Mono 400/700 and Instrument Serif regular/italic. Load them with `@font-face` from a `file://` page. Don't fetch Google Fonts at render time; that hung the first test.
- Apple Color Emoji renders correctly in headless Chrome.

## Not done

### The visuals were not built
A safety classifier stopped the assistant partway through writing the scene file, and the assistant was told not to produce that content again. No reason was given; the project itself is a sandboxed safety eval with fake credentials. As a result:
- `$SCRATCH/web/index.html` is **truncated and unusable**. Delete it or start fresh.
- There are no rendered frames and no video file.
- The peer review of the assistant's video work hasn't happened, because there is no video to review.

If this looks like a false positive, report it with `/feedback` in Claude Code.

### Remaining steps
1. **Build the visuals** for 0–176 s in any tool: Remotion, After Effects, Canva, Keynote export, or a hand-written page using the Playwright setup above. Line the beats up with the audio cue points: voice segments from `intro_transcript.json`, the impact at 52.0 s, section changes at 53, 95 and 152 s, the dropout at 128–130 s and the fade from 170 s.
   - Take the numbers from `report.ipynb`, using `report.py` for the exact tables.
   - Keep the report's caveats visible somewhere: hackathon scale, small cells, one simulated forum, provider-filter exclusions for Claude Sonnet 5.5 and Gemini 3.8 Flash, and a ~35% token-misuse baseline with no swarm.
2. **Mix**:
   - Put the intro at 0 s at full level, `music.wav` underneath at about -6 to -10 dB relative, and the SFX at chosen times via `adelay`.
   - Use `loudnorm` to reach about -14 LUFS integrated.
   - Example:
     ```
     ffmpeg -i video.mp4 -i intro.m4a -i music.wav -i sfx_impact.wav -filter_complex \
       "[1:a]volume=1.0[v];[2:a]volume=0.45[m];[3:a]adelay=52000|52000[s];[v][m][s]amix=inputs=3:normalize=0,loudnorm=I=-14:TP=-1.5[a]" \
       -map 0:v -map "[a]" -c:v copy -c:a aac -b:a 256k -shortest final.mp4
     ```
3. **Peer review**, as the user asked: once a cut exists, have a separate agent review it against `report.ipynb` for factual accuracy, the ≤3:00 length, sync to the voice, legibility and caveats.
4. **Durability**: copy the final video and audio assets out of `/private/tmp`.
