# Design Spec: Notebook 07 — TTS Experiment with Coqui XTTS v2

**Date:** 2026-04-13  
**Project:** WeatherSpeak PH — Gemma 4 Good Hackathon  
**Status:** Approved

---

## Purpose

Prove that the radio bulletin scripts generated in notebook 06 can be synthesized into
playable, downloadable MP3 files using Coqui XTTS v2 — one per language per bulletin.
This is Step 3 of the WeatherSpeak PH ETL pipeline and the last local experiment before
Modal deployment.

---

## Production Context

The full batch ETL pipeline (to be deployed on Modal):

```
PAGASA bulletin arrives (trigger TBD — PAGASA website polling or webhook)
  → Step 1: Gemma 4 E4B  — OCR + chart comprehension → markdown         [nb 04]
  → Step 2: Gemma 4 E4B  — markdown → 5-min radio script, 3 languages   [nb 06]
  → Step 3: XTTS v2      — radio script → MP3, 3 languages               [nb 07]
  → MP3s stored and served for download/playback on website
```

**Not real-time.** MP3 generation runs as a batch job when a new bulletin is detected,
not on user request. Modal is the target runtime for all three steps.

**Model:** Gemma 4 E4B via Ollama for Steps 1–2. A future experiment will test whether
Gemma 4 26B (quantized) can run fast enough on local hardware to be a viable upgrade;
E4B is the working model until that experiment concludes.

---

## Inputs

6 markdown files from `data/radio_bulletins/`:

```
PAGASA_20-19W_Pepito_SWB#01_radio_en.md
PAGASA_20-19W_Pepito_SWB#01_radio_tl.md
PAGASA_20-19W_Pepito_SWB#01_radio_ceb.md
PAGASA_22-TC02_Basyang_TCA#01_radio_en.md
PAGASA_22-TC02_Basyang_TCA#01_radio_tl.md
PAGASA_22-TC02_Basyang_TCA#01_radio_ceb.md
```

Each file is ~600–720 words of markdown prose structured with `##` section headings
and `**bold**` storm names.

---

## Outputs

6 MP3 files written to `data/tts_output/`, mirroring the input naming convention:

```
PAGASA_20-19W_Pepito_SWB#01_radio_en.mp3
PAGASA_20-19W_Pepito_SWB#01_radio_tl.mp3
PAGASA_20-19W_Pepito_SWB#01_radio_ceb.mp3
PAGASA_22-TC02_Basyang_TCA#01_radio_en.mp3
PAGASA_22-TC02_Basyang_TCA#01_radio_tl.mp3
PAGASA_22-TC02_Basyang_TCA#01_radio_ceb.mp3
```

Format: MP3, 128kbps, mono, 24kHz (XTTS v2 native sample rate).  
No intermediate WAV files written to disk.

---

## Architecture

### Text Preprocessing — `preprocess_for_tts(markdown_text: str) -> str`

Converts markdown radio script to speakable plain text:

1. Strip markdown syntax: `##`, `**`, `*`, `_`, backticks
2. Convert section headings into natural pause cues:
   - Replace `## Heading Text` with `\n...\nHeading Text.\n`
   - The ellipsis signals a sentence boundary to XTTS v2, producing a natural pause
3. Strip bold markers from inline text (e.g. `**PEPITO**` → `PEPITO`)
4. Collapse multiple blank lines to one
5. Strip leading/trailing whitespace

### TTS Synthesis — `synthesize_to_mp3(text: str, language: str, output_path: Path) -> Path`

Self-contained, Modal-ready function (no notebook globals):

- **Model:** Coqui XTTS v2 (`tts_models/multilingual/multi-dataset/xtts_v2`)
- **Speaker:** `"Damien Black"` — built-in male voice, authoritative broadcast tone
- **Language mapping:**
  - `en` scripts → `language="en"`
  - `tl` scripts → `language="es"` (Spanish phonemes — best available approximation for Filipino; shares 5-vowel system and consonant inventory with Tagalog/Cebuano)
  - `ceb` scripts → `language="es"`
- **Chunking:** XTTS v2 has a ~200-token synthesis limit. Scripts are split on sentence
  boundaries (`. `, `? `, `! `), synthesized chunk by chunk, numpy arrays concatenated
  in memory before export. Chunking is internal to this function.
- **MP3 export:** Concatenated numpy array → `pydub.AudioSegment` → `.export(format="mp3", bitrate="128k")`. No WAV written to disk.

> **Note — Coqui Tagalog model:** The Coqui TTS model zoo includes a community-contributed
> Tagalog model (`tts_models/tl/...`). This is a future alternative to the Spanish-phoneme
> fallback. Trade-off: native Tagalog phoneme accuracy vs. inconsistent voice (different
> model, different speaker). Worth evaluating once the pipeline is stable.

### Notebook Cell Flow

1. **Setup** — imports, path definitions, `LANGUAGE_MAP = {"en": "en", "tl": "es", "ceb": "es"}`, model load (XTTS v2 downloads ~1.8GB on first run; cached after)
2. **Preprocessing function** — define `preprocess_for_tts()`, run inline test on one sample to verify output looks correct before synthesis
3. **Synthesis function** — define `synthesize_to_mp3()` with chunking and pydub export
4. **Batch run** — loop over all 6 input files, call preprocess → synthesize, print timing and file size per output
5. **Summary** — table: filename, language, duration (seconds), file size (KB), status

---

## Dependencies

| Package | Purpose |
|---|---|
| `coqui-tts` | XTTS v2 model and synthesis |
| `pydub` | In-memory numpy → MP3 conversion |
| `ffmpeg` | System dependency required by pydub |
| `numpy` | Audio array concatenation |

Add to `pyproject.toml` before running.

---

## Modal Extraction Notes

`synthesize_to_mp3(text, language, output_path)` is designed for direct Modal extraction:
- Pure inputs: `str`, `str`, `Path` — no notebook state
- Model loading can be moved to `@app.function(image=...)` build step
- In production, `output_path` becomes an object store write (e.g. Modal Volume or S3)
- The full pipeline (`preprocess → synthesize`) maps naturally to a single Modal function
  triggered per bulletin per language

---

## Future Research

- **Gemma 4 26B quantized:** Experiment with running 26B on local hardware (quantized to 4-bit or 8-bit). If latency is acceptable, 26B becomes the preferred model for Steps 1–2. E4B remains the fallback.
- **Coqui Tagalog model:** Evaluate `tts_models/tl/...` for native phoneme quality vs. voice consistency trade-off.
- **Trigger mechanism:** Determine how new PAGASA bulletins are detected (polling, webhook, scheduled scrape) to complete the ETL pipeline design.
