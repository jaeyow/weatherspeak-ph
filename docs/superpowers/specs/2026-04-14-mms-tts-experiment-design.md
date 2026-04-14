# Notebook 08 — Facebook MMS TTS Experiment Design

**Date:** 2026-04-14  
**Branch:** `feature/tts-experiment`  
**Author:** Jose Reyes

---

## Overview

Evaluate Facebook's Massively Multilingual Speech (MMS) TTS models as a potential replacement for Coqui XTTS v2 in the WeatherSpeak PH pipeline. MMS offers native Cebuano and Tagalog models — eliminating the Spanish phoneme approximation used in notebook 07.

**Scope:** One bulletin (`PAGASA_20-19W_Pepito_SWB#01`), three languages (CEB → TL → EN).

---

## Models

| Language | HuggingFace Model | Params |
|---|---|---|
| Cebuano | `facebook/mms-tts-ceb` | 36.3M |
| Tagalog | `facebook/mms-tts-tgl` | 36.3M |
| English | `facebook/mms-tts-eng` | 36.3M |

- **Architecture:** VITS (end-to-end VAE + HiFi-GAN vocoder)
- **Framework:** HuggingFace Transformers (≥4.33)
- **License:** CC-BY-NC 4.0 (non-commercial — acceptable for hackathon; flag for production)
- **Model size:** ~140MB each in F32, ~420MB total — all three loaded simultaneously (Option B)

---

## Notebook Structure

### Cell 1 — Setup & Paths
- Imports: `transformers`, `torch`, `scipy`, `pydub`, `IPython.display`
- Paths: input from `data/radio_bulletins/`, output to `notebooks/08-mms-tts-experiment/`
- Constants: stem (`PAGASA_20-19W_Pepito_SWB#01`), language order (`ceb`, `tl`, `en`)

### Cell 2 — Text Preprocessing
- Copy `preprocess_for_tts()` from nb 07 (notebooks cannot import each other)
- Preprocess all 3 scripts upfront; save intermediate plain text files alongside MP3s
- Preview preprocessed CEB text for inspection

### Cell 3 — Load All 3 Models
- Load `VitsModel` + `AutoTokenizer` for each language in one block
- Store in a `models` dict keyed by language code: `{"ceb": ..., "tl": ..., "en": ...}`
- Confirm all 3 loaded successfully

### Cell 4 — Synthesis
- `synthesize_with_mms(text, model, tokenizer, output_path)` function:
  - Tokenize text → `model(**inputs).waveform`
  - Convert float32 waveform → int16 PCM → pydub `AudioSegment` → MP3 at 128kbps
  - No chunking required (VITS processes full text in one pass, unlike XTTS v2)
- Run synthesis in order: CEB → TL → EN
- Time each independently; print size and estimated audio duration per file

### Cell 5 — Manual Assessment
- `IPython.display.Audio` widget for each MP3 (listen inline in notebook)
- Pre-structured assessment dict — user fills in scores after listening:

```python
assessment = {
    "ceb": {"quality_score": None,  # 1–5
             "natural_filipino": None,  # 1–5
             "notes": ""},
    "tl":  {"quality_score": None,
             "natural_filipino": None,
             "notes": ""},
    "en":  {"quality_score": None,
             "natural_filipino": None,
             "notes": ""},
}
```

### Cell 6 — Comparison Table
- Combines manual assessment scores + automated speed/size metrics
- Side-by-side: MMS TTS vs XTTS v2 (XTTS v2 CEB result from nb 07 hardcoded; EN/TL not run)
- Columns: Model, Language, Synthesis Time, Audio Duration, MP3 Size, Quality Score, Naturalness Score, Notes
- Conclusion cell: recommendation on whether MMS replaces XTTS v2, partially or fully

---

## Output Files

All saved to `notebooks/08-mms-tts-experiment/` (tracked in git):

```
PAGASA_20-19W_Pepito_SWB#01_radio_ceb.mp3
PAGASA_20-19W_Pepito_SWB#01_radio_ceb_plain.txt
PAGASA_20-19W_Pepito_SWB#01_radio_tl.mp3
PAGASA_20-19W_Pepito_SWB#01_radio_tl_plain.txt
PAGASA_20-19W_Pepito_SWB#01_radio_en.mp3
PAGASA_20-19W_Pepito_SWB#01_radio_en_plain.txt
```

---

## .gitignore Changes

Add exceptions mirroring notebook 07:

```gitignore
!notebooks/08-mms-tts-experiment/
!notebooks/08-mms-tts-experiment/**
!notebooks/08-mms-tts-experiment/*.mp3
```

---

## Dependencies

Add to `pyproject.toml`:
- `scipy>=1.11.0` — waveform to WAV/PCM conversion
- `transformers>=4.33.0` already pinned (check compatibility with existing coqui-tts upper bound `<=4.46.2`)

No new GPU requirements — VITS inference is fast on CPU.

---

## Success Criteria

- All 3 MP3s generated successfully
- CEB and TL audio is intelligible and more natural-sounding than XTTS v2's Spanish-phoneme output
- Synthesis time per file is measurably faster than XTTS v2's 821s (CEB baseline from nb 07)
- Comparison table gives a clear recommendation: replace, partially replace, or keep XTTS v2

---

## Known Constraints

- **CC-BY-NC 4.0** — production use requires either a commercial licence or switching to an alternative model
- **Single voice per model** — no speaker selection (unlike XTTS v2's named speakers)
- **No chunking** — VITS processes full text in one pass; very long inputs may hit tokenizer limits
- **Non-deterministic** — output varies per run unless seed is fixed; fix seed in synthesis function for reproducibility
