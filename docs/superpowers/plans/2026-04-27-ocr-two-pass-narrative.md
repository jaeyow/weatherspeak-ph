# Updated Two-Pass OCR — Focused Narrative Extraction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the broad `_ocr_pdf()` OCR prompt with a focused, field-explicit `_extract_narrative()` that explicitly excludes the forecast table, add three new schema fields, and validate against 4 representative bulletins.

**Architecture:** Two targeted LLM passes — `_extract_narrative()` (all pages, narrative fields only, table excluded) and `_extract_forecast_table()` (page 1, table only, unchanged) — feed into `_generate_metadata()` which merges both into one `metadata.json`. The only structural change is the prompt and function rename; `run_step1()` orchestration is untouched.

**Tech Stack:** Python 3.12, Gemma 4 E4B via Ollama (`http://localhost:11434`), pytest, uv

---

## File Map

| File | Change |
|---|---|
| `modal_etl/core/ocr.py` | Add 3 schema fields; replace `_OCR_SYSTEM_PROMPT`/`_OCR_USER` with `_NARRATIVE_SYSTEM_PROMPT`/`_NARRATIVE_USER`; update `_METADATA_SYSTEM_PROMPT`; rename `_ocr_pdf` → `_extract_narrative`; update `run_step1` call site |
| `tests/test_schema_validation.py` | Add fixture fields for new schema entries; add 2 new tests |
| `tests/test_core_ocr.py` | Fix monkeypatch target name; add schema property test |
| `notebooks/10-etl-e2e.ipynb` | Add multi-stem loop cell for 4-PDF validation run |

---

### Task 1: Write failing schema tests

**Files:**
- Modify: `tests/test_schema_validation.py`

- [ ] **Step 1: Add new fields to the `sample_valid_metadata` fixture**

In `test_schema_validation.py`, update the `sample_valid_metadata` fixture to include the three new nullable fields. Find the fixture and add after the `"confidence"` line:

```python
@pytest.fixture
def sample_valid_metadata():
    """Minimal valid metadata that satisfies the schema."""
    return {
        "bulletin_type": "TCA",
        "bulletin_number": 1,
        "storm": {
            "name": "TEST",
            "category": "Tropical Depression",
            "international_name": None,
            "wind_signal": None,
        },
        "issuance": {
            "datetime": "2025-01-01T00:00:00",
            "valid_until": None,
        },
        "current_position": {
            "latitude": 14.5,
            "longitude": 121.0,
            "reference": "East of Manila",
            "as_of": None,
        },
        "intensity": {
            "max_sustained_winds_kph": 45,
            "gusts_kph": 55,
        },
        "movement": {
            "direction": "Westward",
            "speed_kph": 20,
        },
        "wind_extent": None,
        "land_hazards": None,
        "track_outlook": None,
        "forecast_positions": [
            {
                "hour": 24,
                "label": "24-hour forecast",
                "latitude": 14.6,
                "longitude": 120.5,
                "reference": "East of Manila Bay",
            }
        ],
        "affected_areas": {
            "signal_1": [],
            "signal_2": [],
            "signal_3": [],
            "signal_4": [],
            "signal_5": [],
            "rainfall_warning": [],
            "coastal_waters": None,
        },
        "storm_track_map": {
            "current_position_shown": True,
            "forecast_track_shown": True,
            "description": "Storm track map",
        },
        "confidence": 0.95,
    }
```

- [ ] **Step 2: Add two new tests at the bottom of the file**

```python
def test_new_fields_present_in_schema_properties():
    """wind_extent, land_hazards, track_outlook must exist in schema properties."""
    props = PAGASA_JSON_SCHEMA["properties"]
    assert "wind_extent" in props
    assert "land_hazards" in props
    assert "track_outlook" in props


def test_new_fields_accept_null_and_string(sample_valid_metadata):
    """New fields accept null (already in fixture) and non-null string values."""
    sample_valid_metadata["wind_extent"] = "Winds of at least 30 km/h extend outward up to 280 km"
    sample_valid_metadata["land_hazards"] = "Moderate to heavy rainfall expected in Visayas"
    sample_valid_metadata["track_outlook"] = "The storm is expected to make landfall within 24 hours"
    validate(instance=sample_valid_metadata, schema=PAGASA_JSON_SCHEMA)
```

- [ ] **Step 3: Run the new tests — expect FAIL**

```bash
uv run pytest tests/test_schema_validation.py::test_new_fields_present_in_schema_properties tests/test_schema_validation.py::test_new_fields_accept_null_and_string -v
```

Expected: `FAILED` — `AssertionError` because `wind_extent` not yet in schema properties.

---

### Task 2: Add three new fields to `PAGASA_JSON_SCHEMA`

**Files:**
- Modify: `modal_etl/core/ocr.py`

- [ ] **Step 1: Add the three new properties to `PAGASA_JSON_SCHEMA`**

In `modal_etl/core/ocr.py`, inside `PAGASA_JSON_SCHEMA["properties"]`, add after the `"movement"` block (around line 64) and before `"forecast_positions"`:

```python
        "wind_extent": {"type": ["string", "null"]},
        "land_hazards": {"type": ["string", "null"]},
        "track_outlook": {"type": ["string", "null"]},
```

- [ ] **Step 2: Run the new tests — expect PASS**

```bash
uv run pytest tests/test_schema_validation.py::test_new_fields_present_in_schema_properties tests/test_schema_validation.py::test_new_fields_accept_null_and_string -v
```

Expected: `PASSED`

- [ ] **Step 3: Run the full schema test suite to confirm no regressions**

```bash
uv run pytest tests/test_schema_validation.py -v
```

Expected: all tests `PASSED`

- [ ] **Step 4: Commit**

```bash
git add modal_etl/core/ocr.py tests/test_schema_validation.py
git commit -m "feat: add wind_extent, land_hazards, track_outlook to PAGASA_JSON_SCHEMA"
```

---

### Task 3: Write failing test for `_extract_narrative` rename

**Files:**
- Modify: `tests/test_core_ocr.py`

- [ ] **Step 1: Fix the monkeypatch target in the force-rerun test**

In `tests/test_core_ocr.py`, find `test_run_step1_force_reruns_even_when_outputs_exist`. Change the monkeypatch line from:

```python
monkeypatch.setattr("modal_etl.core.ocr._ocr_pdf", lambda pages, url, model: (called.append(1), "# forced")[1])
```

to:

```python
monkeypatch.setattr("modal_etl.core.ocr._extract_narrative", lambda pages, url, model: (called.append(1), "# forced")[1])
```

- [ ] **Step 2: Add a test that `_extract_narrative` is importable**

Add after the existing tests:

```python
def test_extract_narrative_is_callable():
    """_extract_narrative must exist and be callable (replaces _ocr_pdf)."""
    from modal_etl.core.ocr import _extract_narrative
    assert callable(_extract_narrative)
```

- [ ] **Step 3: Run these tests — expect FAIL**

```bash
uv run pytest tests/test_core_ocr.py::test_run_step1_force_reruns_even_when_outputs_exist tests/test_core_ocr.py::test_extract_narrative_is_callable -v
```

Expected: `FAILED` — `AttributeError: module has no attribute '_extract_narrative'`

---

### Task 4: Replace `_ocr_pdf` with `_extract_narrative` and update prompts

**Files:**
- Modify: `modal_etl/core/ocr.py`

- [ ] **Step 1: Replace `_OCR_SYSTEM_PROMPT` and `_OCR_USER` with the new narrative prompt constants**

Remove the entire `_OCR_SYSTEM_PROMPT` and `_OCR_USER` constants (lines 116–147) and replace with:

```python
_NARRATIVE_SYSTEM_PROMPT = (
    "You are an expert OCR assistant for PAGASA Philippine weather bulletins issued by "
    "the Philippine Atmospheric, Geophysical and Astronomical Services Administration.\n\n"
    "Extract ONLY the following fields from the bulletin pages. "
    "Output clean Markdown preserving headings and lists.\n\n"
    "FIELDS TO EXTRACT:\n"
    "- Bulletin type and number\n"
    "- Storm current name, former name (if any), international name (if any)\n"
    "- Issue date and time\n"
    "- Headline (the short all-caps summary line, "
    "e.g. '\"VERBENA\" WEAKENS WHILE MOVING WEST SOUTHWESTWARD SLOWLY')\n"
    "- Location of Center (coordinates + reference landmark + as-of time)\n"
    "- Intensity (max sustained winds + gusts in km/h)\n"
    "- Present Movement (direction + speed)\n"
    "- Extent of Tropical Cyclone Winds (narrative, "
    "e.g. 'Winds of at least 30 km/h extend outward up to 280 km from the center')\n"
    "- Tropical Cyclone Wind Signals in Effect (list of areas per signal level)\n"
    "- Other Hazards Affecting Land Areas (rainfall advisory, storm surge, flooding)\n"
    "- Hazards Affecting Coastal Waters\n"
    "- Track and Intensity Outlook (narrative forecast summary paragraph)\n"
    "- Storm track map: describe what you see — storm position, forecast track, "
    "affected regions, symbols and legend items\n\n"
    "DO NOT EXTRACT: The 'Track and Intensity Forecast' table. "
    "It appears at the bottom of page 1 as a multi-column table with rows labeled "
    "'12-Hour Forecast', '24-Hour Forecast', etc. "
    "Stop before it and do not read any of its contents."
)

_NARRATIVE_USER = (
    "Extract all narrative bulletin fields and describe the storm track map "
    "from this PAGASA typhoon bulletin image. Do not include the forecast table."
)
```

- [ ] **Step 2: Replace `_METADATA_SYSTEM_PROMPT` with the updated version**

Find and replace the entire `_METADATA_SYSTEM_PROMPT` constant with:

```python
_METADATA_SYSTEM_PROMPT = (
    "You are PAGASAParseAI, an expert at converting extracted PAGASA typhoon bulletin text into structured JSON.\n\n"
    "Extract only the fields listed in the schema. Do not include full_text or any free-form text dump.\n\n"
    "CRITICAL RULES:\n"
    "- Output ONLY the JSON object. No preamble, no markdown fences, no explanation.\n"
    "- If a field cannot be determined, use null or an empty array. Never hallucinate.\n"
    "- forecast_positions must include every position shown (24h, 48h, 72h, 96h, 120h).\n"
    "- FORMER NAME: If a former/previous name is mentioned, extract it into the former_name field. "
    "Otherwise set former_name to null. Current storm name can be empty or null if not found.\n"
    "- HEADLINE: Extract the short all-caps summary line that appears near the top of the bulletin "
    "(e.g. '\"VERBENA\" WEAKENS WHILE MOVING WEST SOUTHWESTWARD SLOWLY'). "
    "It is typically found in the Remarks or General Remarks section. "
    "Capture it exactly as written including any quotation marks around the storm name. "
    "If not present, set headline to null.\n\n"
    "NEW FIELDS — extract these if present in the bulletin text:\n"
    "- wind_extent: narrative string describing how far cyclone winds extend outward "
    "(e.g. 'Winds of at least 30 km/h extend outward up to 280 km from the center'). "
    "Set null if not stated.\n"
    "- land_hazards: narrative string covering rainfall advisories, storm surge warnings, "
    "and flooding warnings for land areas. Set null if none.\n"
    "- track_outlook: the Track and Intensity Outlook narrative paragraph. "
    "Set null if not present."
)
```

- [ ] **Step 3: Rename `_ocr_pdf` → `_extract_narrative` and update its internals**

Find the `_ocr_pdf` function (starts around line 217) and replace it entirely with:

```python
def _extract_narrative(pages, ollama_url: str, model: str) -> str:
    pages_md = []
    for i, page in enumerate(pages):
        img_b64 = _page_to_b64(page)
        page_md = call_ollama_generate(
            url=ollama_url,
            model=model,
            prompt=_NARRATIVE_USER,
            system=_NARRATIVE_SYSTEM_PROMPT,
            images_b64=[img_b64],
            timeout=OLLAMA_TIMEOUT,
        )
        pages_md.append(f"<!-- Page {i + 1} -->\n\n{page_md}")
    return "\n\n---\n\n".join(pages_md)
```

- [ ] **Step 4: Update the `run_step1` call site**

In `run_step1`, find the block that calls `_ocr_pdf` (around line 325):

```python
    if not ocr_path.exists() or force:
        markdown = _ocr_pdf(pages, ollama_url, model)
```

Change to:

```python
    if not ocr_path.exists() or force:
        markdown = _extract_narrative(pages, ollama_url, model)
```

- [ ] **Step 5: Run the previously failing tests — expect PASS**

```bash
uv run pytest tests/test_core_ocr.py::test_run_step1_force_reruns_even_when_outputs_exist tests/test_core_ocr.py::test_extract_narrative_is_callable -v
```

Expected: `PASSED`

- [ ] **Step 6: Run the full OCR test suite**

```bash
uv run pytest tests/test_core_ocr.py -v
```

Expected: all tests `PASSED`

- [ ] **Step 7: Commit**

```bash
git add modal_etl/core/ocr.py tests/test_core_ocr.py
git commit -m "feat: replace _ocr_pdf with _extract_narrative — focused field-explicit prompt, excludes forecast table"
```

---

### Task 5: Run the full test suite

**Files:** none modified

- [ ] **Step 1: Run all tests**

```bash
uv run pytest tests/ -v
```

Expected: all tests `PASSED`. If any fail, check the error — the most likely cause is a monkeypatch still referencing `_ocr_pdf` somewhere else.

- [ ] **Step 2: Commit if any test fixes were needed**

```bash
git add tests/
git commit -m "fix: update remaining test references after _ocr_pdf → _extract_narrative rename"
```

---

### Task 6: Add multi-stem notebook cell and validate against 4 PDFs

**Files:**
- Modify: `notebooks/10-etl-e2e.ipynb`

- [ ] **Step 1: Add a new cell at the top of notebook 10 for multi-stem validation**

Add a new markdown cell before the existing Step 1 cell:

```markdown
## Multi-Bulletin Validation (4 PDFs)

Runs Step 1 (OCR + metadata) across 4 representative bulletins to validate the
updated two-pass narrative extraction. Set `STEMS` to the 4 PDFs open in your IDE.
```

Then add a code cell:

```python
from modal_etl.core.ocr import run_step1
from pathlib import Path
import json

OLLAMA_URL = "http://localhost:11434"
ARCHIVE_ROOT = Path("../data/bulletin-archive/archive")
OUTPUT_DIR = Path("10-etl-e2e/output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Set these to the 4 PDFs open in your IDE
STEMS = [
    ("pagasa-20-19W", "PAGASA_20-19W_Pepito_SWB#01"),
    ("pagasa-22-TC02", "PAGASA_22-TC02_Basyang_TCA#01"),
    ("pagasa-25-TC22", "PAGASA_25-TC22_Verbena_TCB#24"),
    ("pagasa-26-TC02", "PAGASA_26-TC02_Basyang_TCB#01"),
]

for archive_subdir, stem in STEMS:
    pdf_path = ARCHIVE_ROOT / archive_subdir / f"{stem}.pdf"
    print(f"\n{'='*60}")
    print(f"Processing: {stem}")
    print(f"PDF exists: {pdf_path.exists()}")
    stem_dir = run_step1(pdf_path, OUTPUT_DIR, ollama_url=OLLAMA_URL, force=True)
    print(f"Done → {stem_dir}")
```

- [ ] **Step 2: Add a validation cell to inspect outputs**

```python
# Validate outputs for each stem
for _, stem in STEMS:
    stem_dir = OUTPUT_DIR / stem
    print(f"\n{'='*60}")
    print(f"Stem: {stem}")

    # Check ocr.md does NOT contain forecast table rows
    ocr_md = (stem_dir / "ocr.md").read_text(encoding="utf-8")
    table_leaked = "12-Hour Forecast" in ocr_md or "24-Hour Forecast" in ocr_md
    print(f"  ocr.md: {len(ocr_md)} chars | forecast table leaked: {table_leaked}")

    # Check forecast_table.md exists and has content
    ft_md = (stem_dir / "forecast_table.md").read_text(encoding="utf-8")
    print(f"  forecast_table.md: {len(ft_md)} chars")

    # Check new fields in metadata.json
    meta = json.loads((stem_dir / "metadata.json").read_text(encoding="utf-8"))
    print(f"  wind_extent:  {meta.get('wind_extent')}")
    print(f"  land_hazards: {meta.get('land_hazards')}")
    print(f"  track_outlook: {meta.get('track_outlook')}")
    fp_count = len(meta.get("forecast_positions", []))
    print(f"  forecast_positions: {fp_count} rows")
```

- [ ] **Step 3: Run the notebook top-to-bottom**

In Jupyter, `Kernel > Restart & Run All`. Confirm:
- `forecast table leaked: False` for all 4 stems
- `wind_extent`, `land_hazards`, `track_outlook` are non-null strings (not `None`) for bulletins that contain those sections
- `forecast_positions` has 8 rows (the standard PAGASA forecast table)

- [ ] **Step 4: Commit**

```bash
git add notebooks/10-etl-e2e.ipynb
git commit -m "feat: add multi-stem validation cell to notebook 10 for two-pass OCR testing"
```
