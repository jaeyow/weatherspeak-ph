---
title: Updated Two-Pass OCR — Focused Narrative Extraction
date: 2026-04-27
status: approved
---

# Updated Two-Pass OCR — Focused Narrative Extraction

## Problem

The current broad OCR pass (`_ocr_pdf`) sends the full bulletin page to Gemma 4 E4B with a generic "transcribe everything" instruction. When the model encounters the dense multi-column Track and Intensity Forecast table, it hallucinates — producing incorrect forecast values that bleed into the narrative fields and corrupt `metadata.json`.

## Solution

Replace the broad OCR prompt with a focused, field-explicit extraction prompt that explicitly names and excludes the forecast table. Each LLM call has a single, unambiguous task.

---

## Architecture

### Two passes (unchanged structure, updated prompts and schema)

**Pass 1 — `_extract_narrative()` (replaces `_ocr_pdf()`)**
- Processes all pages (narrative fields span pages 1–3)
- Prompt explicitly lists every field to extract
- Prompt explicitly excludes the forecast table by name and row-label pattern
- Output: `ocr.md` (clean Markdown of all narrative fields + storm chart description)

**Pass 2 — `_extract_forecast_table()` (unchanged)**
- Processes page 1 only
- Same focused table prompt as today
- Output: `forecast_table.md`

**Metadata generation — `_generate_metadata()` (structure unchanged)**
- Takes `narrative_md` + `forecast_table_md` as inputs
- Uses updated `PAGASA_JSON_SCHEMA` (3 new fields)
- `forecast_positions` still in schema — sourced exclusively from Pass 2 table
- Output: single merged `metadata.json`

### What stays the same
- `_extract_forecast_table()` — prompt and logic unchanged
- `_find_chart_page()` — unchanged
- `run_step1()` — only the internal call changes (`_ocr_pdf` → `_extract_narrative`); all file paths, skip logic, and force flag behaviour unchanged
- Step 2 (radio scripts) — reads `ocr.md`; unaffected

---

## New `_NARRATIVE_SYSTEM_PROMPT`

```
You are an expert OCR assistant for PAGASA Philippine weather bulletins.

Extract ONLY the following fields from the bulletin pages. Output clean Markdown
preserving headings and lists.

FIELDS TO EXTRACT:
- Bulletin type and number
- Storm current name, former name (if any), international name (if any)
- Issue date and time
- Headline (the short all-caps summary line, e.g. '"VERBENA" WEAKENS...')
- Location of Center (coordinates + reference landmark + as-of time)
- Intensity (max sustained winds + gusts in km/h)
- Present Movement (direction + speed)
- Extent of Tropical Cyclone Winds (narrative, e.g. "Winds of at least 30 km/h
  extend outward up to 280 km from the center")
- Tropical Cyclone Wind Signals in Effect (list of areas per signal level)
- Other Hazards Affecting Land Areas (rainfall advisory, storm surge, flooding)
- Hazards Affecting Coastal Waters
- Track and Intensity Outlook (narrative forecast summary)
- Storm track map: describe the chart — storm position, forecast track,
  affected regions, legend items

DO NOT EXTRACT: The "Track and Intensity Forecast" table. It appears at the
bottom of page 1 as a multi-column table with rows labeled "12-Hour Forecast",
"24-Hour Forecast", etc. Stop before it and do not read any of its contents.
```

---

## Schema Changes

Three fields added to `PAGASA_JSON_SCHEMA`. `forecast_positions` remains — it is populated by `_generate_metadata()` using the Pass 2 table, not from the narrative OCR.

```python
"wind_extent":   {"type": ["string", "null"]},
"land_hazards":  {"type": ["string", "null"]},
"track_outlook": {"type": ["string", "null"]},
```

`_METADATA_SYSTEM_PROMPT` updated with extraction guidance for each new field:
- `wind_extent` — narrative string for cyclone wind radius (null if not stated)
- `land_hazards` — rainfall advisory, storm surge, flooding warnings for land areas (null if none)
- `track_outlook` — the Track and Intensity Outlook narrative paragraph (null if not present)

### Final `metadata.json` shape

```
bulletin_type, bulletin_number
storm { name, former_name, international_name, category, wind_signal }
issuance { datetime, valid_until }
current_position { lat, lon, reference, as_of }
intensity { max_sustained_winds_kph, gusts_kph }
movement { direction, speed_kph }
wind_extent          ← NEW
affected_areas { signal_1…5, rainfall_warning, coastal_waters }
land_hazards         ← NEW
track_outlook        ← NEW
storm_track_map { current_position_shown, forecast_track_shown, description }
forecast_positions   ← sourced exclusively from Pass 2 forecast_table.md
headline
confidence
```

---

## Testing

**Test corpus:** 4 representative PAGASA bulletin PDFs open in the IDE.

**Run:** `run_step1()` with `force=True` against all 4.

**Success criteria:**
1. `ocr.md` contains all Pass 1 narrative fields — no forecast table rows present
2. `forecast_table.md` extracts cleanly (unchanged behaviour)
3. `metadata.json` — `wind_extent`, `land_hazards`, `track_outlook` non-null for bulletins that contain those sections
4. `forecast_positions` in `metadata.json` matches `forecast_table.md` exactly — no hallucinated rows
5. Step 2 radio script generation is unaffected

A multi-stem loop cell can be added to notebook 10 to run all 4 PDFs in one pass.
