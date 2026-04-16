# XTTS v2 English Experiment — Notebook 07 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Change notebook 07's test synthesis cell to run English instead of Cebuano, producing an XTTS v2 English MP3 for quality evaluation.

**Architecture:** Single-cell edit in notebook 07. Change `TEST_LANG = "ceb"` to `TEST_LANG = "en"`. All other cells (model load, preprocessing, synthesis function) are untouched — XTTS v2 and `LANGUAGE_MAP["en"] = "en"` are already in place.

**Tech Stack:** Coqui XTTS v2 (`tts_models/multilingual/multi-dataset/xtts_v2`), Jupyter notebook

---

### Task 1: Update the test cell to synthesize English

**Files:**
- Modify: `notebooks/07-tts-experiment.ipynb` — cell id `ed198279` (cell index 8)

- [ ] **Step 1: Edit the test cell**

Change `TEST_LANG` from `"ceb"` to `"en"` in cell `ed198279`.

The cell should read:

```python
# --- TEST MODE: single file ---
# Change to full STEMS / LANGUAGES loop once preprocessing is validated
TEST_STEM = "PAGASA_20-19W_Pepito_SWB#01"
TEST_LANG = "en"

results = []

for stem, lang in [(TEST_STEM, TEST_LANG)]:
    input_path = input_dir / f"{stem}_radio_{lang}.md"
    output_path = output_dir / f"{stem}_radio_{lang}.mp3"
    plain_path = output_dir / f"{stem}_radio_{lang}_plain.txt"
    xtts_lang = LANGUAGE_MAP[lang]

    lang_label = {"en": "English", "tl": "Tagalog", "ceb": "Cebuano"}[lang]
    print(f"\nSynthesizing: {stem} ({lang_label}) → {xtts_lang} phoneme")

    markdown = input_path.read_text(encoding="utf-8")
    plain = preprocess_for_tts(markdown)

    # Save intermediate plain text for inspection
    plain_path.write_text(plain, encoding="utf-8")
    print(f"  ✓ Intermediate text saved → {plain_path.name}")

    chunks = chunk_text(plain)

    t_start = time.time()
    synthesize_to_mp3(plain, xtts_lang, output_path, tts, speaker=SPEAKER, sample_rate=SAMPLE_RATE)
    elapsed = time.time() - t_start

    size_kb = output_path.stat().st_size // 1024
    duration_s = (size_kb * 1024 * 8) / 128_000

    print(f"  ✓ {elapsed:.1f}s  |  {size_kb} KB  |  ~{duration_s:.0f}s audio")
    print(f"  ✓ MP3 → {output_path.name}")

    results.append({
        "stem": stem.replace("PAGASA_", ""),
        "language": lang_label,
        "xtts_lang": xtts_lang,
        "chunks": len(chunks),
        "elapsed_s": round(elapsed, 1),
        "size_kb": size_kb,
        "duration_s": round(duration_s),
        "path": str(output_path),
    })

print(f"\n✓ Done")
```

The only diff from the current cell is line 3: `TEST_LANG = "en"`.

- [ ] **Step 2: Verify input file exists**

```bash
ls data/radio_bulletins/PAGASA_20-19W_Pepito_SWB#01_radio_en.md
```

Expected: file listed (it exists as of this writing).

- [ ] **Step 3: Run the notebook top-to-bottom and listen**

Run all cells in order in Jupyter. The synthesis cell will:
- Read `data/radio_bulletins/PAGASA_20-19W_Pepito_SWB#01_radio_en.md`
- Preprocess markdown → plain text
- Save plain text to `data/tts_output/PAGASA_20-19W_Pepito_SWB#01_radio_en_plain.txt`
- Synthesize ~26 chunks via XTTS v2 with speaker "Damien Black", language "en"
- Write `data/tts_output/PAGASA_20-19W_Pepito_SWB#01_radio_en.mp3`

Expected terminal output (approximate):
```
Synthesizing: PAGASA_20-19W_Pepito_SWB#01 (English) → en phoneme
  ✓ Intermediate text saved → PAGASA_20-19W_Pepito_SWB#01_radio_en_plain.txt
  ✓ <elapsed>s  |  <size> KB  |  ~<duration>s audio
  ✓ MP3 → PAGASA_20-19W_Pepito_SWB#01_radio_en.mp3

✓ Done
```

Listen to `data/tts_output/PAGASA_20-19W_Pepito_SWB#01_radio_en.mp3` and assess quality.

- [ ] **Step 4: Commit**

```bash
git add notebooks/07-tts-experiment.ipynb
git commit -m "feat: switch notebook 07 test to English XTTS v2 synthesis"
```
