# Marker OCR Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `backend="marker"` option to `run_step1()` that uses the Marker PDF library instead of Gemma 4 Ollama for text extraction, switchable with one word in the notebook and one CLI flag in Modal.

**Architecture:** A lazy-import dispatch in `run_step1()` delegates to a new `modal_etl/core/ocr_marker.py` module when `backend="marker"`. Marker extracts full markdown (text + tables natively), selects the largest figure as the storm chart, then runs one Gemma 4 vision pass for chart description. `_generate_metadata()` is shared from `ocr.py`. No `forecast_table.md` is produced in Marker mode.

**Tech Stack:** Python 3.12, `marker-pdf>=1.10.0` (already installed in `.venv`), Gemma 4 E4B via Ollama for chart description, Modal for production GPU, pytest + uv

---

## File Map

| File | Change |
|---|---|
| `modal_etl/core/ocr_marker.py` | **Create** — single public `run()` + private helpers |
| `modal_etl/core/ocr.py` | Add `backend` param + lazy dispatch to `run_step1()` |
| `modal_etl/step1_ocr.py` | Add `backend` param to `Step1OCR.run()` + new `Step1OCRMarker` class |
| `modal_etl/app.py` | Add `marker_image` (extends `ollama_image` + `marker-pdf`) |
| `modal_etl/run_batch.py` | Add `--backend` CLI flag, select correct OCR class |
| `notebooks/10-etl-e2e.ipynb` | Add `BACKEND` config var, pass to `run_step1()` |
| `tests/test_core_ocr.py` | Add one delegation test |
| `tests/test_core_ocr_marker.py` | **Create** — skip logic + output contract tests |

---

### Task 1: Write failing test for `run_step1` backend delegation

**Files:**
- Modify: `tests/test_core_ocr.py`

- [ ] **Step 1: Add the failing delegation test**

Open `tests/test_core_ocr.py`. At the bottom, after `test_pagasa_json_schema_has_required_fields`, add:

```python
def test_run_step1_backend_marker_delegates(tmp_path, monkeypatch):
    """run_step1 with backend='marker' delegates to ocr_marker.run()."""
    import sys
    import types

    called = []
    fake_ocr_marker = types.ModuleType("modal_etl.core.ocr_marker")
    fake_ocr_marker.run = lambda *a, **kw: called.append(a) or tmp_path
    monkeypatch.setitem(sys.modules, "modal_etl.core.ocr_marker", fake_ocr_marker)

    pdf_path = tmp_path / "PAGASA_TEST.pdf"
    pdf_path.write_bytes(b"fake pdf")

    result = run_step1(pdf_path, tmp_path, backend="marker")

    assert len(called) == 1
    assert result == tmp_path
```

- [ ] **Step 2: Run — expect FAIL**

```bash
uv run pytest tests/test_core_ocr.py::test_run_step1_backend_marker_delegates -v
```

Expected: `FAILED` — `TypeError: run_step1() got an unexpected keyword argument 'backend'`

- [ ] **Step 3: Commit the failing test**

```bash
git add tests/test_core_ocr.py
git commit -m "test: add failing test for run_step1 backend='marker' delegation"
```

---

### Task 2: Add `backend` parameter and lazy dispatch to `run_step1()`

**Files:**
- Modify: `modal_etl/core/ocr.py`

- [ ] **Step 1: Update `run_step1()` signature and add dispatch**

Find `run_step1()` in `modal_etl/core/ocr.py` (currently starts around line 302). Replace the function signature and add the dispatch block at the very top of the function body, before any existing logic:

```python
def run_step1(
    pdf_path: Path,
    output_dir: Path,
    ollama_url: str = "http://localhost:11434",
    model: str = "gemma4:e4b",
    force: bool = False,
    stem: str | None = None,
    backend: str = "gemma4",
) -> Path:
    """Run OCR on pdf_path and write ocr.md, chart.png, metadata.json to output_dir/{stem}/.

    Returns:
        Path to the stem-scoped output directory (output_dir/{stem}/).
    """
    if backend == "marker":
        from modal_etl.core import ocr_marker
        return ocr_marker.run(pdf_path, output_dir, ollama_url, model, force, stem)

    # --- Gemma 4 path (unchanged below) ---
    stem = stem or pdf_path.stem
    ...
```

Everything after the `if backend == "marker":` block is the existing Gemma 4 logic — leave it untouched.

- [ ] **Step 2: Run the delegation test — expect PASS**

```bash
uv run pytest tests/test_core_ocr.py::test_run_step1_backend_marker_delegates -v
```

Expected: `PASSED`

- [ ] **Step 3: Run full OCR test suite — no regressions**

```bash
uv run pytest tests/test_core_ocr.py -v
```

Expected: all `PASSED`

- [ ] **Step 4: Commit**

```bash
git add modal_etl/core/ocr.py
git commit -m "feat: add backend param to run_step1 with lazy marker dispatch"
```

---

### Task 3: Write failing tests for `ocr_marker.run()`

**Files:**
- Create: `tests/test_core_ocr_marker.py`

- [ ] **Step 1: Create the test file**

Create `tests/test_core_ocr_marker.py` with this full content:

```python
"""Tests for modal_etl/core/ocr_marker.py — skip logic and output contract only."""
from pathlib import Path
import pytest


def _write_marker_outputs(stem_dir: Path) -> None:
    (stem_dir / "ocr.md").write_text("# OCR content", encoding="utf-8")
    (stem_dir / "chart.png").write_bytes(b"fakepng")
    (stem_dir / "metadata.json").write_text('{"bulletin_type": "TCA"}', encoding="utf-8")


def test_run_marker_skips_when_outputs_exist(tmp_path):
    """run() returns stem_dir immediately when ocr.md, chart.png, metadata.json exist and force=False."""
    from modal_etl.core.ocr_marker import run

    stem = "PAGASA_TEST"
    pdf_path = tmp_path / f"{stem}.pdf"
    pdf_path.write_bytes(b"fake pdf")
    stem_dir = tmp_path / stem
    stem_dir.mkdir()
    _write_marker_outputs(stem_dir)

    result = run(pdf_path, tmp_path, force=False)

    assert result == stem_dir


def test_run_marker_force_reruns(tmp_path, monkeypatch):
    """run() with force=True calls _run_marker even when outputs already exist."""
    from modal_etl.core import ocr_marker
    from PIL import Image

    stem = "PAGASA_TEST"
    pdf_path = tmp_path / f"{stem}.pdf"
    pdf_path.write_bytes(b"fake pdf")
    stem_dir = tmp_path / stem
    stem_dir.mkdir()
    _write_marker_outputs(stem_dir)

    called = []
    fake_img = Image.new("RGB", (200, 200))

    monkeypatch.setattr(
        "modal_etl.core.ocr_marker._run_marker",
        lambda p: (called.append(1), ("# markdown", {"fig_0": fake_img}))[1],
    )
    monkeypatch.setattr(
        "modal_etl.core.ocr_marker._select_chart",
        lambda figs: fake_img,
    )
    monkeypatch.setattr(
        "modal_etl.core.ocr_marker._describe_chart",
        lambda path, url, model: "Storm is northwest of Palawan.",
    )
    monkeypatch.setattr(
        "modal_etl.core.ocr_marker._generate_metadata",
        lambda md, url, model, forecast_table_md=None: {
            "bulletin_type": "TCA",
            "storm": {"name": "TEST", "category": "Typhoon"},
            "issuance": {},
            "current_position": {},
            "intensity": {},
            "movement": {},
            "forecast_positions": [],
            "affected_areas": {},
            "storm_track_map": {},
            "confidence": 1.0,
        },
    )

    ocr_marker.run(pdf_path, tmp_path, force=True)

    assert len(called) == 1


def test_marker_does_not_produce_forecast_table_md(tmp_path, monkeypatch):
    """Marker mode never writes forecast_table.md."""
    from modal_etl.core import ocr_marker
    from PIL import Image

    stem = "PAGASA_TEST"
    pdf_path = tmp_path / f"{stem}.pdf"
    pdf_path.write_bytes(b"fake pdf")

    fake_img = Image.new("RGB", (200, 200))

    monkeypatch.setattr(
        "modal_etl.core.ocr_marker._run_marker",
        lambda p: ("# markdown", {"fig_0": fake_img}),
    )
    monkeypatch.setattr(
        "modal_etl.core.ocr_marker._select_chart",
        lambda figs: fake_img,
    )
    monkeypatch.setattr(
        "modal_etl.core.ocr_marker._describe_chart",
        lambda path, url, model: "Storm track description.",
    )
    monkeypatch.setattr(
        "modal_etl.core.ocr_marker._generate_metadata",
        lambda md, url, model, forecast_table_md=None: {
            "bulletin_type": "TCA",
            "storm": {"name": "TEST", "category": "Typhoon"},
            "issuance": {},
            "current_position": {},
            "intensity": {},
            "movement": {},
            "forecast_positions": [],
            "affected_areas": {},
            "storm_track_map": {},
            "confidence": 1.0,
        },
    )

    ocr_marker.run(pdf_path, tmp_path, force=True)

    stem_dir = tmp_path / stem
    assert (stem_dir / "ocr.md").exists()
    assert (stem_dir / "chart.png").exists()
    assert (stem_dir / "metadata.json").exists()
    assert not (stem_dir / "forecast_table.md").exists()
```

- [ ] **Step 2: Run — expect FAIL**

```bash
uv run pytest tests/test_core_ocr_marker.py -v
```

Expected: `ERROR` — `ModuleNotFoundError: No module named 'modal_etl.core.ocr_marker'`

- [ ] **Step 3: Commit the failing tests**

```bash
git add tests/test_core_ocr_marker.py
git commit -m "test: add failing tests for ocr_marker.run() skip logic and output contract"
```

---

### Task 4: Implement `modal_etl/core/ocr_marker.py`

**Files:**
- Create: `modal_etl/core/ocr_marker.py`

- [ ] **Step 1: Create the file with complete content**

```python
"""Marker-based OCR backend for PAGASA typhoon bulletins.

Replaces the two-pass Gemma 4 OCR with:
  1. Marker PDF extraction → full markdown (text + tables natively accurate)
  2. Largest extracted figure → chart.png
  3. One Gemma 4 vision pass on chart.png → storm track description appended to ocr.md
  4. Shared _generate_metadata() → metadata.json

Does NOT produce forecast_table.md — Marker's table extraction is accurate enough
that the metadata LLM can read the table directly from ocr.md.
"""
from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any

from modal_etl.core.ocr import _generate_metadata
from modal_etl.core.ollama import call_ollama_generate

OLLAMA_TIMEOUT = 600

_CHART_DESCRIPTION_SYSTEM = (
    "You are an expert on PAGASA Philippine weather bulletin storm track maps. "
    "Describe what you see in one concise paragraph: the storm's current position, "
    "the forecast track direction, affected regions, and any legend items or symbols visible."
)

_CHART_DESCRIPTION_USER = "Describe this PAGASA storm track map image."

_converter: Any = None


def _get_converter() -> Any:
    """Load Marker PdfConverter once; cache at module level for reuse."""
    global _converter
    if _converter is None:
        from marker.converters.pdf import PdfConverter
        from marker.config.parser import ConfigParser
        from marker.models import create_model_dict

        config_parser = ConfigParser(
            {
                "output_format": "markdown",
                "langs": ["English"],
                "disable_image_extraction": False,
            }
        )
        _converter = PdfConverter(
            artifact_dict=create_model_dict(),
            config=config_parser.generate_config_dict(),
            processor_list=config_parser.get_processors(),
            renderer=config_parser.get_renderer(),
        )
    return _converter


def _run_marker(pdf_path: Path) -> tuple[str, dict]:
    """Run Marker on the PDF. Returns (markdown_str, figures_dict)."""
    from marker.output import text_from_rendered

    converter = _get_converter()
    rendered = converter(str(pdf_path))
    markdown, _, figures = text_from_rendered(rendered)
    return markdown, figures or {}


def _select_chart(figures: dict) -> Any | None:
    """Return the largest figure by pixel area — the storm track map on PAGASA bulletins."""
    if not figures:
        return None
    return max(figures.values(), key=lambda img: img.size[0] * img.size[1])


def _describe_chart(chart_path: Path, ollama_url: str, model: str) -> str:
    """Run one Gemma 4 vision pass on chart_path and return a description string."""
    img_b64 = base64.b64encode(chart_path.read_bytes()).decode("utf-8")
    return call_ollama_generate(
        url=ollama_url,
        model=model,
        prompt=_CHART_DESCRIPTION_USER,
        system=_CHART_DESCRIPTION_SYSTEM,
        images_b64=[img_b64],
        timeout=OLLAMA_TIMEOUT,
    ).strip()


def run(
    pdf_path: Path,
    output_dir: Path,
    ollama_url: str = "http://localhost:11434",
    model: str = "gemma4:e4b",
    force: bool = False,
    stem: str | None = None,
) -> Path:
    """Run Marker OCR on pdf_path. Writes ocr.md, chart.png, metadata.json to output_dir/{stem}/.

    Does NOT write forecast_table.md — Marker handles tables accurately without a separate pass.

    Returns:
        Path to the stem-scoped output directory (output_dir/{stem}/).
    """
    stem = stem or pdf_path.stem
    out_dir = output_dir / stem
    ocr_path = out_dir / "ocr.md"
    chart_path = out_dir / "chart.png"
    metadata_path = out_dir / "metadata.json"

    if ocr_path.exists() and chart_path.exists() and metadata_path.exists() and not force:
        print(f"[run_step1_marker] {stem}: all outputs exist, skipping")
        return out_dir

    out_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: Extract text and figures
    markdown, figures = _run_marker(pdf_path)
    print(f"[run_step1_marker] {stem}: Marker extracted {len(markdown)} chars, {len(figures)} figures")

    # Step 2: Save chart and describe it
    chart_img = _select_chart(figures)
    if chart_img is not None:
        chart_img.save(str(chart_path), format="PNG")
        print(f"[run_step1_marker] {stem}: saved chart.png")
        chart_description = _describe_chart(chart_path, ollama_url, model)
        full_md = markdown + f"\n\n## Storm Track Map\n\n{chart_description}"
    else:
        print(f"[run_step1_marker] {stem}: no figures extracted, skipping chart")
        chart_path.write_bytes(b"")
        full_md = markdown

    ocr_path.write_text(full_md, encoding="utf-8")
    print(f"[run_step1_marker] {stem}: wrote ocr.md ({len(full_md)} chars)")

    # Step 3: Generate metadata from full markdown (table included)
    metadata = _generate_metadata(full_md, ollama_url, model)
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[run_step1_marker] {stem}: wrote metadata.json")

    return out_dir
```

- [ ] **Step 2: Run the Task 3 tests — expect PASS**

```bash
uv run pytest tests/test_core_ocr_marker.py -v
```

Expected: all 3 tests `PASSED`

- [ ] **Step 3: Run full test suite — no regressions**

```bash
uv run pytest tests/ -v
```

Expected: all tests `PASSED`

- [ ] **Step 4: Commit**

```bash
git add modal_etl/core/ocr_marker.py
git commit -m "feat: implement ocr_marker.py — Marker-based OCR backend with Gemma 4 chart description"
```

---

### Task 5: Wire `backend` through `step1_ocr.py` and `run_batch.py`

**Files:**
- Modify: `modal_etl/step1_ocr.py`
- Modify: `modal_etl/run_batch.py`

- [ ] **Step 1: Add `backend` param to `Step1OCR.run()` in `step1_ocr.py`**

Find `Step1OCR.run()` (line 34). Update the method signature and the `run_step1` call:

```python
    @modal.method()
    def run(self, pdf_url: str, force: bool = False, backend: str = "gemma4") -> str:
        """Download PDF from URL and run step 1 OCR pipeline.

        Returns:
            stem string (filename without .pdf extension).
        """
        stem = unquote(pdf_url.split("/")[-1].replace(".pdf", ""))
        resp = requests.get(pdf_url, timeout=60)
        resp.raise_for_status()
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(resp.content)
            pdf_path = Path(f.name)
        run_step1(pdf_path, OUTPUT_PATH, OLLAMA_URL, GEMMA_MODEL, force, stem=stem, backend=backend)
        output_volume.commit()
        return stem
```

- [ ] **Step 2: Add `--backend` to `run_batch.py::main()` and pass through**

Find the `main()` function signature in `modal_etl/run_batch.py` (around line 220). Add `backend`:

```python
def main(n: int = N_EVENTS, force: bool = False, stem: str = "", step: int = 0, backend: str = "gemma4") -> None:
```

Find the `ocr.run.remote()` call (around line 271). Add `backend`:

```python
                stem = ocr.run.remote(bulletin.pdf_url, force=force, backend=backend)
```

- [ ] **Step 3: Run the full test suite**

```bash
uv run pytest tests/ -v
```

Expected: all tests `PASSED` (these are integration wiring changes with no new test paths to cover)

- [ ] **Step 4: Commit**

```bash
git add modal_etl/step1_ocr.py modal_etl/run_batch.py
git commit -m "feat: wire backend param through Step1OCR.run() and run_batch.py --backend flag"
```

---

### Task 6: Add `marker_image` to `app.py` and `Step1OCRMarker` to `step1_ocr.py`

**Files:**
- Modify: `modal_etl/app.py`
- Modify: `modal_etl/step1_ocr.py`
- Modify: `modal_etl/run_batch.py`

- [ ] **Step 1: Add `marker_image` to `app.py`**

In `modal_etl/app.py`, after the `ollama_image` definition, add:

```python
# Container image for Step 1 in Marker mode — extends ollama_image with marker-pdf
# marker-pdf pulls torch + surya-ocr; Ollama is still needed for chart description.
marker_image = ollama_image.pip_install("marker-pdf>=1.10.0")
```

- [ ] **Step 2: Add `Step1OCRMarker` class to `step1_ocr.py`**

In `modal_etl/step1_ocr.py`, update the imports to include `marker_image`:

```python
from modal_etl.app import app, ollama_image, marker_image, OLLAMA_MOUNTS, output_volume
```

Then add the new class after `Step1OCR`:

```python
@app.cls(
    image=marker_image,
    gpu="A10G",
    volumes=OLLAMA_MOUNTS,
    timeout=3600,
)
class Step1OCRMarker:
    @modal.enter()
    def start_ollama(self) -> None:
        """Start Ollama server (needed for chart description pass)."""
        import os
        os.environ["OLLAMA_MODELS"] = str(OLLAMA_MODELS_PATH)
        subprocess.Popen(["ollama", "serve"])
        wait_for_ollama(OLLAMA_URL)
        print("[Step1OCRMarker] Ollama ready")

    @modal.method()
    def run(self, pdf_url: str, force: bool = False) -> str:
        """Download PDF and run Marker OCR pipeline.

        Returns:
            stem string (filename without .pdf extension).
        """
        stem = unquote(pdf_url.split("/")[-1].replace(".pdf", ""))
        resp = requests.get(pdf_url, timeout=60)
        resp.raise_for_status()
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(resp.content)
            pdf_path = Path(f.name)
        run_step1(pdf_path, OUTPUT_PATH, OLLAMA_URL, GEMMA_MODEL, force, stem=stem, backend="marker")
        output_volume.commit()
        return stem
```

Note: `Step1OCRMarker` hardcodes `backend="marker"` — no need to pass it dynamically since the class itself is the backend selection.

- [ ] **Step 3: Update `run_batch.py` to select the correct OCR class**

In `modal_etl/run_batch.py`, update the imports:

```python
from modal_etl.step1_ocr import Step1OCR, Step1OCRMarker
```

In `main()`, replace the `ocr = Step1OCR()` instantiation with backend-aware selection:

```python
    ocr = Step1OCRMarker() if backend == "marker" else Step1OCR()
```

And simplify the `ocr.run.remote()` call (no more `backend` kwarg since the class handles it):

```python
                stem = ocr.run.remote(bulletin.pdf_url, force=force)
```

- [ ] **Step 4: Run the full test suite**

```bash
uv run pytest tests/ -v
```

Expected: all tests `PASSED`

- [ ] **Step 5: Commit**

```bash
git add modal_etl/app.py modal_etl/step1_ocr.py modal_etl/run_batch.py
git commit -m "feat: add marker_image and Step1OCRMarker for Modal Marker backend support"
```

---

### Task 7: Update notebook 10

**Files:**
- Modify: `notebooks/10-etl-e2e.ipynb`

- [ ] **Step 1: Add `BACKEND` to the config cell**

In `notebooks/10-etl-e2e.ipynb`, find the config cell (cell `cell-2`). Add one line after `FORCE_RUN`:

The full updated config cell source should be:

```python
# ── Configuration ────────────────────────────────────────────────────────
STEM          = "PAGASA_25-TC22_Verbena_TCB#24"
PDF_PATH      = Path("../data/bulletin-archive/archive/pagasa-25-TC22") / f"{STEM}.pdf"
OUTPUT_DIR    = Path("10-etl-e2e/output")
OLLAMA_URL    = "http://localhost:11434"
LANGUAGES     = ["ceb", "tl", "en"]
TTS_MODELS_DIR = Path.home() / ".cache" / "huggingface" / "hub"
FORCE_RUN     = True
BACKEND       = "gemma4"   # swap to "marker" to use Marker OCR

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
print(f"PDF:        {PDF_PATH}  (exists={PDF_PATH.exists()})")
print(f"Output dir: {OUTPUT_DIR.resolve()}")
print(f"Ollama URL: {OLLAMA_URL}")
print(f"Backend:    {BACKEND}")
```

- [ ] **Step 2: Update the `run_step1` call in the Step 1 cell**

Find the Step 1 code cell (cell `cell-7`). Its first line currently reads:

```python
stem_dir = run_step1(PDF_PATH, OUTPUT_DIR, ollama_url=OLLAMA_URL, force=FORCE_RUN)
```

Change it to:

```python
stem_dir = run_step1(PDF_PATH, OUTPUT_DIR, ollama_url=OLLAMA_URL, force=FORCE_RUN, backend=BACKEND)
```

- [ ] **Step 3: Commit**

```bash
git add notebooks/10-etl-e2e.ipynb
git commit -m "feat: add BACKEND config var to notebook 10 — swap OCR with one word"
```

---

### Task 8: Run full test suite and validate

**Files:** none modified

- [ ] **Step 1: Run all tests**

```bash
uv run pytest tests/ -v
```

Expected: all tests `PASSED`. If any fail, fix before proceeding.

- [ ] **Step 2: Smoke-test Marker locally in the notebook**

In `notebooks/10-etl-e2e.ipynb`:
1. Set `BACKEND = "marker"` in the config cell
2. Set `FORCE_RUN = True`
3. Run the config cell + Step 1 cell only
4. Confirm `ocr.md`, `chart.png`, and `metadata.json` are written to `10-etl-e2e/output/{STEM}/`
5. Confirm `forecast_table.md` is **absent**
6. Check `metadata.json` has non-null `forecast_positions` (Marker's table was read directly)
7. Check `ocr.md` ends with `## Storm Track Map` section

Note: Marker model loading takes ~3 minutes on first run (models download to `~/.cache/datalab/`). Subsequent runs reuse the cache and are faster.
