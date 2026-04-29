---
title: English-First Radio Script Generation
date: 2026-04-29
status: approved
---

# English-First Radio Script Generation

## Problem

Step 2 generates radio scripts for English, Tagalog, and Cebuano independently — each reads the same OCR markdown and metadata and produces a script in one pass. In practice the English output is significantly more complete: it captures storm track, Signal levels, affected areas, and action guidance reliably. Tagalog and Cebuano outputs regularly drop information because the LLM reasons less accurately in those languages when working from raw structured data.

## Solution

Generate English first. Once `radio_en.md` exists, produce Tagalog and Cebuano by adapting the English script rather than generating independently from the bulletin data. This guarantees TL/CEB inherit the full data already extracted by the English pass. The TTS pipeline downstream is unchanged.

---

## Architecture

### Files changed

| File | Change |
|---|---|
| `modal_etl/core/scripts.py` | Add `_TRANSLATE_PROMPTS`, add `_translate_radio_script()`, update `run_step2()` dispatch |
| `modal_etl/run_batch.py` | Split `starmap` into EN-first then TL+CEB parallel |
| `tests/test_core_scripts.py` | Add three new tests for the EN-first dispatch logic |

No changes to `modal_etl/step2_scripts.py`, `modal_etl/core/tts.py`, or any TTS-related code.

---

## `scripts.py` — Changes

### New: `_TRANSLATE_PROMPTS`

A dict with `"tl"` and `"ceb"` entries. Each entry has:

- **`"system"`** — identical to the corresponding entry in `_RADIO_PROMPTS` (reused directly, no duplication). All existing constraints apply: PURO TAGALOG / PURO CEBUANO, priority order, style rules, 200-word limit, plain prose only.
- **`"user"`** — new template that takes `{english_script}` instead of `{bulletin_data}`. Instructs the model to adapt the English into natural Tagalog/Cebuano and explicitly forbids dropping any detail.

Tagalog user template:
```
Narito ang kumpletong pahayag sa Ingles tungkol sa bagyo. I-adapt ito sa natural na Tagalog.

{english_script}

MAHALAGA: Panatilihin ang LAHAT ng impormasyon mula sa Ingles — pangalan ng bagyo,
lokasyon, landas, bawat apektadong lugar na may Signal level, kung ano ang dapat gawin,
at oras ng susunod na update. Walang detalye ang maaaring maiwanan.

Isulat ang pahayag sa Tagalog ngayon. Hindi hihigit sa 200 salita.
Puro Tagalog. Walang headings, walang markdown.
```

Cebuano user template — same structure written in Cebuano.

### New: `_translate_radio_script(english_md, language, ollama_url, model)`

```python
def _translate_radio_script(english_md: str, language: str, ollama_url: str, model: str) -> str:
    p = _TRANSLATE_PROMPTS[language]
    return call_ollama_chat(
        url=ollama_url,
        model=model,
        system=p["system"],
        user=p["user"].format(english_script=english_md),
    )
```

### Updated: `run_step2()` dispatch

After reading `ocr_md` and `metadata`, `run_step2()` branches on `language`:

```python
if language == "en":
    radio_md = _generate_radio_script(ocr_md, "en", ollama_url, model, metadata=metadata)
else:
    # Ensure English script exists — generate it now if missing
    en_radio_path = out_dir / "radio_en.md"
    if not en_radio_path.exists():
        en_radio_md = _generate_radio_script(ocr_md, "en", ollama_url, model, metadata=metadata)
        en_radio_path.write_text(en_radio_md, encoding="utf-8")
    english_md = en_radio_path.read_text(encoding="utf-8")
    radio_md = _translate_radio_script(english_md, language, ollama_url, model)
```

Everything after `radio_md` is assigned — `_generate_tts_text`, `_cleanup_english_words`, `_cleanup_numbers` — is unchanged for all three languages.

---

## `run_batch.py` — Changes

Replace the single `starmap` call for all three languages with a two-phase call:

```python
# Phase 1: English first (synchronous)
step2_scripts.remote(stem, "en", force)

# Phase 2: Tagalog and Cebuano in parallel (both translate from radio_en.md)
list(step2_scripts.starmap([(stem, "tl", force), (stem, "ceb", force)]))
```

This prevents TL and CEB Modal containers from racing to generate `radio_en.md` simultaneously.

---

## Skip logic

`run_step2()` skip logic is unchanged: if `radio_{lang}.md` and `tts_{lang}.txt` both exist and `force=False`, return immediately. The auto-EN generation only runs when TL/CEB is requested and `radio_en.md` is absent.

---

## Testing

### New tests in `tests/test_core_scripts.py`

| Test | What it verifies |
|---|---|
| `test_run_step2_tl_generates_en_first_if_missing` | When `radio_en.md` does not exist and `language="tl"`, `_generate_radio_script` is called for EN first, then `_translate_radio_script` is called for TL |
| `test_run_step2_tl_uses_english_when_en_exists` | When `radio_en.md` already exists, `_translate_radio_script` is called directly without calling `_generate_radio_script` |
| `test_run_step2_en_path_unchanged` | For `language="en"`, `_generate_radio_script` is called and `_translate_radio_script` is never called |

### Existing tests — no changes needed

`test_run_step2_skips_when_outputs_exist`, `test_run_step2_raises_when_ocr_missing`, `test_clean_ocr_*`, and all `test_step2_format_metadata.py` tests are unaffected.
