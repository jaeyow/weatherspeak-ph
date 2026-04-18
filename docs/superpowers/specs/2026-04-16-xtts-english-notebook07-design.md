# XTTS v2 English Experiment — Notebook 07

**Date:** 2026-04-16
**Scope:** Notebook 07 only — no modal_etl changes

---

## Goal

Validate Coqui XTTS v2 for English TTS quality by synthesizing the Pepito English
radio bulletin directly in notebook 07. SpeechT5 produced unacceptable audio quality;
XTTS v2 is already proven for CEB in this notebook.

---

## Change

**File:** `notebooks/07-tts-experiment.ipynb`

One cell updated — the test synthesis cell currently hardcoded to `TEST_LANG = "ceb"`:

- Set `TEST_LANG = "en"`
- Input: `data/radio_bulletins/PAGASA_20-19W_Pepito_SWB#01_radio_en.md` (exists)
- Output: `data/tts_output/PAGASA_20-19W_Pepito_SWB#01_radio_en.mp3`
- XTTS language code: `"en"` (native — from existing `LANGUAGE_MAP`)
- Speaker: `"Damien Black"` (unchanged)
- Everything else — model load, `preprocess_for_tts`, `chunk_text`, `synthesize_to_mp3` — is untouched

No other files change.

---

## Success Criteria

- English MP3 generates without error
- Audio is clear, natural-sounding English (subjective listen test)
- If quality is good → proceed to wire XTTSSynthesizer into modal_etl in a follow-up
