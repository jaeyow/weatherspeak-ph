# ETL Modularization + Notebook 10 (End-to-End Local Pipeline)

**Date:** 2026-04-26  
**Branch:** `feature/nb10-etl-modularization`  
**Goal:** Extract reusable pure-Python core modules from `modal_etl/` so the same business logic runs both inside Modal GPU containers and locally in a Jupyter notebook (nb-10).

---

## Problem

The three ETL step files (`step1_ocr.py`, `step2_scripts.py`, `step3_tts.py`) mix business logic with Modal infrastructure (decorators, volume mounts, container images). This makes it impossible to import and run the pipeline logic locally without the Modal SDK configured. Notebook 10 needs to run the full PDF→MP3 pipeline on a local machine using the same code that runs in production.

---

## Approach

Extract all pure-Python business logic into a new `modal_etl/core/` sub-package. The existing step files become thin `@app.function` / `@app.cls` wrappers (~10 lines each) that call `modal_etl.core.*`. The notebook imports directly from `modal_etl.core.*`.

This is a **refactor-in-place** — no new top-level packages, no duplication, no protocol/dependency-injection complexity. The synthesizers in `modal_etl/synthesizers/` are already Modal-agnostic and stay where they are.

---

## Package Structure

### New files

```
modal_etl/core/__init__.py
modal_etl/core/ollama.py     # shared Ollama HTTP helpers
modal_etl/core/ocr.py        # PDF → OCR markdown + metadata JSON
modal_etl/core/scripts.py    # radio scripts + TTS text generation
modal_etl/core/tts.py        # sentence prep + step3 runner
```

### Refactored (thinned to Modal wrappers)

```
modal_etl/step1_ocr.py       # @app.cls wrapper → calls core/ocr.py
modal_etl/step2_scripts.py   # @app.function wrapper → calls core/scripts.py
modal_etl/step3_tts.py       # @app.function wrapper → calls core/tts.py
```

### New notebook

```
notebooks/10-etl-e2e.ipynb
notebooks/10-etl-e2e/output/{stem}/   # mirrors /output/{stem}/ on Modal
```

---

## Module Interfaces

### `core/ollama.py`

Consolidates `_wait_for_ollama()` (currently duplicated in `step1_ocr.py` and `step2_scripts.py`) plus vision and chat call helpers.

```python
def wait_for_ollama(url: str, retries: int = 60, delay: float = 2.0) -> None: ...
def call_ollama_vision(url: str, model: str, prompt: str, b64_image: str) -> str: ...
def call_ollama_chat(url: str, model: str, system: str, user: str) -> str: ...
```

### `core/ocr.py`

Accepts a local `Path`. Modal wrapper downloads from URL then writes a temp file before calling this.

```python
def run_step1(
    pdf_path: Path,
    output_dir: Path,
    ollama_url: str = "http://localhost:11434",
    model: str = "gemma4:e4b",
    force: bool = False,
) -> Path:  # returns output_dir/{stem}/
```

Writes: `ocr.md`, `chart.png`, `metadata.json` under `output_dir/{stem}/`.  
`stem` is derived from `pdf_path.stem`.  
Private helpers moved from `step1_ocr.py`: `_pdf_to_pil_pages`, `_page_to_b64`, `_ocr_pdf`, `_find_chart_page`, `_generate_metadata`.

### `core/scripts.py`

Reads from `output_dir/{stem}/` written by step 1.

```python
def run_step2(
    stem: str,
    language: str,
    output_dir: Path,
    ollama_url: str = "http://localhost:11434",
    model: str = "gemma4:e4b",
    force: bool = False,
) -> Path:  # returns output_dir/{stem}/radio_{language}.md
```

Writes: `radio_{lang}.md`, `tts_{lang}.txt` under `output_dir/{stem}/`.  
Private helpers moved from `step2_scripts.py`: `_format_metadata_for_prompt`, `_clean_ocr`, `_generate_radio_script`, `_generate_tts_text`, `_cleanup_english_words`, `_cleanup_numbers`.

### `core/tts.py`

Sentence prep functions moved here from `step3_tts.py` (which imports them back). Adds `run_step3` so the notebook can call TTS without importing Modal.

```python
def prepare_mms_sentences(text: str) -> list[tuple[str, bool]]: ...
def prepare_english_sentences(text: str) -> list[tuple[str, bool]]: ...

def run_step3(
    stem: str,
    language: str,
    output_dir: Path,
    tts_models_dir: Path,
    force: bool = False,
) -> Path:  # returns output_dir/{stem}/audio_{language}.mp3
```

Reads: `tts_{lang}.txt`. Writes: `audio_{lang}.mp3`. Uses `modal_etl/synthesizers/` unchanged.

---

## Modal Step Wrappers (after refactor)

Public signatures of `step1_ocr.run(pdf_url, force)`, `step2_scripts(stem, language, force)`, and `step3_tts(stem, language, force)` **do not change**. Bodies shrink to:

1. Resolve paths using `OUTPUT_PATH` (Modal Volume mount)
2. Call `core.*:run_step*(..., output_dir=OUTPUT_PATH, ...)`
3. Call `output_volume.commit()`

---

## Data Flow

```
PDF (local path)
  │
  ▼ core/ocr.py:run_step1()
  ├── output/{stem}/ocr.md
  ├── output/{stem}/chart.png
  └── output/{stem}/metadata.json
        │
        ▼ core/scripts.py:run_step2()  [× 3 languages]
        ├── output/{stem}/radio_{lang}.md
        └── output/{stem}/tts_{lang}.txt
              │
              ▼ core/tts.py:run_step3()  [× 3 languages]
              └── output/{stem}/audio_{lang}.mp3
```

---

## Notebook 10 — Cell Layout

**File:** `notebooks/10-etl-e2e.ipynb`  
**Output dir:** `notebooks/10-etl-e2e/output/{stem}/`

| Cell | Type | Content |
|------|------|---------|
| 0 | markdown | Title + goal |
| 1 | code | Imports + `sys.path` for `modal_etl` |
| 2 | code | Config: `STEM`, `PDF_PATH`, `OUTPUT_DIR`, `OLLAMA_URL`, `LANGUAGES`, `TTS_MODELS_DIR` |
| 3 | markdown | `## Step 1: OCR — PDF → Markdown + Metadata` |
| 4 | code | `run_step1(PDF_PATH, OUTPUT_DIR)` → preview `ocr.md` + pretty-print `metadata.json` |
| 5 | markdown | `## Step 2: Radio Scripts + TTS Text` |
| 6 | code | Loop `LANGUAGES`: `run_step2(stem, lang, OUTPUT_DIR)` → preview radio scripts |
| 7 | markdown | `## Step 3: TTS Synthesis → MP3` |
| 8 | code | Loop `LANGUAGES`: `run_step3(stem, lang, OUTPUT_DIR, TTS_MODELS_DIR)` |
| 9 | code | `IPython.display.Audio` players for all generated MP3s |
| 10 | markdown | `## Output Summary` |
| 11 | code | Walk `OUTPUT_DIR/{stem}/` → print artefact tree with file sizes |

**Config defaults:**
```python
STEM           = "PAGASA_22-TC02_Basyang_TCA#01"
PDF_PATH       = Path("../data/pdfs") / f"{STEM}.pdf"
OUTPUT_DIR     = Path("10-etl-e2e/output")
OLLAMA_URL     = "http://localhost:11434"
LANGUAGES      = ["en", "tl", "ceb"]
TTS_MODELS_DIR = Path.home() / ".cache" / "huggingface" / "hub"
```

`force=False` by default. Set `force=True` in individual cells to re-run a step.

---

## Skip Logic

| Step | Skipped if all exist |
|------|----------------------|
| `run_step1` | `ocr.md`, `chart.png`, `metadata.json` |
| `run_step2` | `radio_{lang}.md`, `tts_{lang}.txt` |
| `run_step3` | `audio_{lang}.mp3` |

---

## What Does NOT Change

- `modal_etl/synthesizers/` — already Modal-agnostic
- `modal_etl/phonetics.py` — already Modal-agnostic
- `modal_etl/config.py` — Modal Volume paths stay; `core/*` accept `output_dir` as parameter
- `modal_etl/app.py`, `modal_etl/run_batch.py` — no changes
- Public signatures of all three step functions — no changes

---

## Out of Scope

- Frontend / Supabase upload (step 4)
- Batch multi-bulletin runs in nb-10 (single stem only)
- PDF download from GitHub archive in nb-10 (local file only)
