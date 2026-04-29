---
title: Marker OCR Backend — Swappable OCR for WeatherSpeak PH
date: 2026-04-28
status: approved
---

# Marker OCR Backend — Swappable OCR

## Problem

The current OCR pipeline uses Gemma 4 E4B via Ollama for all extraction. The forecast table required a dedicated second pass (`forecast_table.md`) to work around hallucination on dense multi-column tables. A traditional OCR alternative (Marker) handles tables accurately natively and may produce better structured text for some bulletins — but there was no way to compare or switch backends without rewriting the pipeline.

## Solution

Add a `backend` parameter to `run_step1()`. When `backend="marker"`, it lazy-imports `modal_etl/core/ocr_marker.py` and delegates entirely. When `backend="gemma4"` (default), existing logic is untouched. One word/flag difference at every invocation point.

---

## Architecture

### Files

| File | Change |
|---|---|
| `modal_etl/core/ocr_marker.py` | **New** — all Marker logic, single public `run()` function |
| `modal_etl/core/ocr.py` | Add `backend` param + lazy-import dispatch in `run_step1()` |
| `modal_etl/step1_ocr.py` | Add `backend` param to `Step1OCR.run()`, pass to `run_step1()` |
| `modal_etl/run_batch.py` | Add `--backend` CLI flag to `main()` |
| `notebooks/10-etl-e2e.ipynb` | Add `BACKEND` config var, pass to `run_step1()` |
| `tests/test_core_ocr_marker.py` | **New** — skip logic and output contract tests |
| `tests/test_core_ocr.py` | Add one delegation test for `backend="marker"` |

### Swap Points

| Context | Gemma 4 (default) | Marker |
|---|---|---|
| Notebook 10 | `BACKEND = "gemma4"` | `BACKEND = "marker"` |
| Modal batch | `modal run run_batch.py` | `modal run run_batch.py --backend marker` |
| Single bulletin | `modal run run_batch.py --stem X --force` | `modal run run_batch.py --stem X --force --backend marker` |

---

## `ocr.py` — `run_step1()` Change

Add `backend: str = "gemma4"` parameter. When `"marker"` is passed, lazy-import `ocr_marker` inside the function body (so Marker's models are never loaded in Gemma 4 mode) and delegate:

```python
def run_step1(pdf_path, output_dir, ollama_url, model, force, stem, backend="gemma4"):
    if backend == "marker":
        from modal_etl.core import ocr_marker
        return ocr_marker.run(pdf_path, output_dir, ollama_url, model, force, stem)
    # ... existing Gemma 4 logic unchanged ...
```

No other changes to `ocr.py`.

---

## `ocr_marker.py` — Marker Backend

### Single public function: `run(pdf_path, output_dir, ollama_url, model, force, stem)`

Same signature and same output directory contract as `run_step1()`.

### Internal steps

**1. Model loading — lazy module-level cache**

```python
_converter = None

def _get_converter():
    global _converter
    if _converter is None:
        from marker.converters.pdf import PdfConverter
        from marker.models import create_model_dict
        from marker.config.parser import ConfigParser
        config_parser = ConfigParser({
            "output_format": "markdown",
            "langs": ["English"],
            "disable_image_extraction": False,
        })
        _converter = PdfConverter(
            artifact_dict=create_model_dict(),
            config=config_parser.generate_config_dict(),
            processor_list=config_parser.get_processors(),
            renderer=config_parser.get_renderer(),
        )
    return _converter
```

Models (~2 GB) are downloaded once and cached by Marker in `~/.cache/datalab/`. Subsequent calls reuse the loaded converter.

**2. PDF → markdown + figures**

`PdfConverter` runs directly on the PDF path. Returns full markdown (all text and tables in reading order) and a dict of extracted figure images (`{name: PIL.Image}`). No PDF-to-image conversion step needed.

**3. `ocr.md` — Marker's full markdown**

Marker's native table handling is accurate — no hallucination workaround needed. The forecast table is included in the markdown as a proper Markdown table alongside the narrative text. The full markdown is written to `ocr.md` without filtering.

The chart description (step 5) is appended as a `## Storm Track Map` section at the end of `ocr.md`.

**4. Chart identification → `chart.png`**

Marker returns all extracted figures. Select the largest by pixel area — on PAGASA bulletins the storm track map is always the dominant figure. Save as `chart.png`.

**5. Chart description — one Gemma 4 vision pass**

Send `chart.png` to Gemma 4 via `call_ollama_generate()` with a focused prompt:

> "You are an expert on PAGASA Philippine weather bulletin storm track maps. Describe what you see: storm current position, forecast track direction, affected regions, and any legend items or symbols visible."

The response is appended to `ocr.md` as `## Storm Track Map\n\n{description}`.

**6. Metadata — shared `_generate_metadata()`**

```python
from modal_etl.core.ocr import _generate_metadata
metadata = _generate_metadata(ocr_md, ollama_url, model)
```

Called **without** `forecast_table_md` — `_generate_metadata()` already supports this (the param is optional, defaulting to `None`). The full `ocr.md` contains the forecast table and the LLM extracts `forecast_positions` from it directly.

### Output contract

| File | Produced? |
|---|---|
| `ocr.md` | ✅ Full Marker markdown + chart description |
| `forecast_table.md` | ❌ Not produced — not needed in Marker mode |
| `chart.png` | ✅ Largest extracted figure |
| `metadata.json` | ✅ Same schema as Gemma 4 mode |

### Skip logic

Marker mode checks for `ocr.md` + `chart.png` + `metadata.json` (no `forecast_table.md` check):

```python
if ocr_path.exists() and chart_path.exists() and metadata_path.exists() and not force:
    print(f"[run_step1_marker] {stem}: all outputs exist, skipping")
    return out_dir
```

---

## Modal ETL Changes

### `step1_ocr.py`

`Step1OCR.run()` gains `backend: str = "gemma4"` and passes it to `run_step1()`. No other changes.

### `run_batch.py`

One new parameter alongside `--stem` and `--force`:

```python
@app.local_entrypoint()
def main(stem: str = "", force: bool = False, backend: str = "gemma4"):
    ...
    ocr.run.remote(bulletin.pdf_url, force=force, backend=backend)
```

---

## Notebook 10 Changes

One new line in the config cell:

```python
BACKEND = "gemma4"   # swap to "marker" to use Marker OCR
```

Passed to `run_step1()`:

```python
stem_dir = run_step1(PDF_PATH, OUTPUT_DIR, ollama_url=OLLAMA_URL, force=FORCE_RUN, backend=BACKEND)
```

---

## Testing

### New: `tests/test_core_ocr_marker.py`

| Test | What it verifies |
|---|---|
| `test_run_marker_skips_when_outputs_exist` | Returns `stem_dir` immediately when `ocr.md`, `chart.png`, `metadata.json` exist and `force=False` |
| `test_run_marker_force_reruns` | Monkeypatches `_get_converter` and `_generate_metadata`; confirms they're called when `force=True` |
| `test_marker_does_not_produce_forecast_table_md` | Confirms `forecast_table.md` is absent after a mocked run |

### Addition to `tests/test_core_ocr.py`

| Test | What it verifies |
|---|---|
| `test_run_step1_backend_marker_delegates` | Monkeypatches `modal_etl.core.ocr_marker.run`; confirms it's called when `backend="marker"` is passed to `run_step1()` |

No changes to `test_schema_validation.py` — schema is backend-agnostic.
