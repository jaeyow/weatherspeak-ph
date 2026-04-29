# WeatherSpeak PH — Development Log

Ongoing record of progress made during the Gemma 4 Good Hackathon (deadline: May 18, 2026).
Each entry corresponds to a pull request or significant milestone.

---

## PR #20 — ETL Modularization, Marker OCR Backend, English-First Scripts
**Date:** 2026-04-29
**Branch:** `feature/ocr-prompt-improvements`
**Status:** Complete ✅

### What we built

A large refactor and feature pass covering five areas:

1. **`modal_etl/core/` — ETL modularization** into testable, reusable modules
2. **Notebook 10** — end-to-end local ETL pipeline using the new `core/` modules
3. **Two-pass OCR** — focused narrative extraction + dedicated forecast table pass
4. **Marker OCR backend** — alternative Step 1 backend using Marker PDF instead of Gemma 4 vision
5. **English-first radio script generation** — TL/CEB now translate from the English output

---

#### 1. `modal_etl/core/` — ETL Modularization

Extracted all business logic out of the Modal step files into a standalone `modal_etl/core/` package. The step files (`step1_ocr.py`, `step2_scripts.py`, `step3_tts.py`) are now thin wrappers that set up the Modal runtime, call the core module, and return.

| Module | Responsibility |
|---|---|
| `modal_etl/core/ollama.py` | Shared Ollama HTTP helpers (`call_ollama_generate`, `call_ollama_chat`) |
| `modal_etl/core/ocr.py` | Step 1 logic: page rendering, two-pass OCR, metadata generation |
| `modal_etl/core/scripts.py` | Step 2 logic: `run_step2()`, all prompts, EN-first dispatch |
| `modal_etl/core/tts.py` | Step 3 logic: MMS + Coqui XTTS v2 synthesis |
| `modal_etl/core/ocr_marker.py` | Marker OCR backend: Marker + Gemma 4 chart description |

**Benefit:** All core logic is now importable locally for notebook development and unit testing — no Modal container needed.

#### 2. Notebook 10 — End-to-End Local ETL

`notebooks/10-etl-e2e.ipynb` — runs the full pipeline locally using `modal_etl/core/` modules. Supports both OCR backends (`BACKEND = "gemma4"` or `"marker"`) with a single variable change.

Validation cells run after each step to verify output files and structure.

#### 3. Two-Pass OCR

**Problem:** Single-pass Gemma 4 OCR produced hallucinations on the forecast track table (coordinates, wind speeds) because the model was attempting to process the full page in one call.

**Fix:** Split Step 1 into two targeted passes:
- **Pass 1 (`_extract_narrative`)** — focused prompt on storm narrative fields only (position, intensity, movement, affected areas). Explicitly excludes the forecast table.
- **Pass 2 (`_extract_forecast_table`)** — dedicated pass on page 1 only, extracting the 24h/48h/72h/96h/120h forecast positions table.

Both passes are merged before `_generate_metadata()`. `forecast_table.md` is saved alongside `ocr.md` for inspection.

Also added `wind_extent`, `land_hazards`, and `track_outlook` fields to `PAGASA_JSON_SCHEMA`.

#### 4. Marker OCR Backend

Alternative Step 1 backend: **Marker PDF** (Surya-based layout-aware PDF extractor) + one Gemma 4 vision pass for chart description.

**Why Marker:** Gemma 4 vision sometimes hallucinates on dense table content. Marker extracts text and tables natively at near-100% accuracy, matching the native PDF text. The storm track chart still needs vision comprehension — Gemma 4 handles that in a single targeted pass on the extracted figure.

**How to use:**
- Notebook 10: `BACKEND = "marker"`
- `run_batch.py`: `--backend marker`

**Key implementation details:**
- `_select_chart()` filters figures by aspect ratio (height/width ≥ 0.2) and minimum area (100k px) to reject banner-shaped headers — returns `None` if no figure qualifies; caller falls back to `pdf2image` first page
- If no suitable figure extracted (map embedded in page layout), first PDF page rendered via `pdf2image` as fallback chart
- Does NOT produce `forecast_table.md` — Marker's table extraction is accurate enough that the metadata LLM reads it directly from `ocr.md`

**Modal deployment fixes for Marker:**
- `marker_image` uses shared `_ollama_base` (without `add_local_python_source`) then chains `pip_install(torch)` → `pip_install(marker-pdf)` → `add_local_python_source("modal_etl")` last — Modal errors if build steps follow a local mount
- Pinned `marker-pdf>=1.7.0,<1.8.0` (surya-ocr 0.14.7): version 1.6.x used surya-ocr 0.13.1 which cannot read current S3 model weights — produces `KeyError: 'encoder'` on cold Modal containers
- `marker_image` requires CUDA torch (`extra_index_url=https://download.pytorch.org/whl/cu121`) for surya-ocr GPU acceleration

#### 5. English-First Radio Script Generation

**Problem:** All three languages (EN, TL, CEB) were generated independently from raw OCR data. Gemma 4 is more accurate in English — TL/CEB scripts sometimes omitted details or invented locations.

**Fix:** EN is generated first; TL/CEB are translated/adapted from the English output.

```
EN script ─────────────────────────────► radio_en.md
              ↓ _translate_radio_script()
TL reads radio_en.md ──────────────────► radio_tl.md
CEB reads radio_en.md ─────────────────► radio_ceb.md
```

- `_TRANSLATE_PROMPTS` dict (TL + CEB) — adaptation prompts that pass `{english_script}` as context; reuses same system prompt object from `_RADIO_PROMPTS` (identity, not a copy)
- `_translate_radio_script()` — single Ollama chat call per language
- `run_step2()` dispatch: if `language == "en"` → generate; else → read `radio_en.md` (auto-generate EN if missing) → translate
- `force=True` regenerates `radio_en.md` even when it exists (prevents stale base)
- `run_batch.py` two-phase dispatch: `step2_scripts.remote(stem, "en", force)` synchronously first → then `starmap` for TL+CEB in parallel — prevents Modal race condition where both containers race to create `radio_en.md`

### Files changed

| File | Change |
|---|---|
| `modal_etl/core/ollama.py` | New — shared Ollama HTTP helpers |
| `modal_etl/core/ocr.py` | New — Step 1 core logic (two-pass OCR, metadata generation) |
| `modal_etl/core/scripts.py` | New — Step 2 core logic with `_TRANSLATE_PROMPTS`, `_translate_radio_script()`, EN-first `run_step2()` |
| `modal_etl/core/tts.py` | New — Step 3 core logic (MMS + XTTS v2) |
| `modal_etl/core/ocr_marker.py` | New — Marker OCR backend with `_select_chart()` and chart description |
| `modal_etl/app.py` | Extract `_ollama_base`; `marker_image` with CUDA torch + `add_local_python_source` last |
| `modal_etl/step1_ocr.py` | Thin wrapper + `Step1OCRMarker` class for `--backend marker` |
| `modal_etl/step2_scripts.py` | Thin wrapper delegating to `core/scripts.py` |
| `modal_etl/step3_tts.py` | Thin wrapper delegating to `core/tts.py` |
| `modal_etl/run_batch.py` | EN-first two-phase Step 2 dispatch; `--backend` flag |
| `notebooks/10-etl-e2e.ipynb` | New — end-to-end local ETL pipeline with `BACKEND` config var |
| `tests/test_core_ocr.py` | New — unit tests for `core/ocr.py` |
| `tests/test_core_scripts.py` | New + extended — EN-first dispatch tests including `force=True` |
| `tests/test_core_ocr_marker.py` | New — `_select_chart` filter tests + skip/force contract |

**191 tests passing.**

---

## PR #18 — Pipeline Validation Notebook + OCR Artefact Cleanup
**Date:** 2026-04-25
**Branch:** `feature/bug-fixes-script-lang-stem`
**Status:** Complete ✅

### What we built

Two improvements to the ETL quality pipeline:

1. **`notebooks/09-pipeline-validation.ipynb`** — end-to-end pipeline validation notebook that exercises all four pipeline steps (metadata generation → radio scripts → TTS text → audio synthesis) across three sample bulletins, with schema validation and quality checks at every stage.

2. **OCR artefact cleanup in Step 2** — a preprocessing pass that strips bracket placeholders from `ocr.md` before it reaches the script-generation LLM, preventing bracket-pattern hallucination in the generated scripts.

---

#### 1. Notebook 09 — Pipeline Validation

The notebook tests three bulletins end-to-end:

| Stem | Type | Storm |
|---|---|---|
| `PAGASA_20-19W_Pepito_SWB#01` | Severe Weather Bulletin | Tropical Depression Pepito |
| `PAGASA_22-TC02_Basyang_TCA#01` | Tropical Cyclone Alert | Basyang |
| `PAGASA_25-TC22_Verbena_TCB#24` | Tropical Cyclone Bulletin #24 | Typhoon Verbena (OUTSIDE PAR) |

**Key innovation — hybrid LLM input:**

`generate_radio_bulletin()` provides both structured JSON metadata and the full OCR markdown to the LLM in a single prompt:

```python
user_prompt = f"""Convert this PAGASA weather bulletin into a plain conversational announcement.

=== KEY FACTS (structured data for quick reference) ===
{json.dumps(structured_metadata, indent=2, ensure_ascii=False)}

=== FULL BULLETIN TEXT (complete information) ===
{ocr_markdown}

Write the announcement now. Use the structured data to quickly identify key facts,
but rely on the full bulletin text for accuracy and completeness. ..."""
```

This addresses the hallucination bugs found in PR #14 (wind speed confused with movement speed, wrong storm name in Basyang script) by giving the LLM pre-parsed, labelled fields as a quick-reference anchor while keeping full OCR text available for completeness.

**Synthesis pipeline** (reused from notebook 08):

| Language | TTS Model | Notes |
|---|---|---|
| Cebuano | `facebook/mms-tts-ceb` (VITS) | Native phonemes |
| Tagalog | `facebook/mms-tts-tgl` (VITS) | Native phonemes |
| English | Coqui XTTS v2 (`Damien Black`) | Better prosody than MMS English |

**Validation steps:**

- **Schema validation**: `jsonschema.validate()` against `PAGASA_JSON_SCHEMA` — catches missing required fields and type mismatches
- **Coordinate range checks**: latitude −90 to 90, longitude 0 to 360
- **Radio script completeness**: word count check, no raw Markdown in output
- **TTS text quality**: no leftover Markdown syntax (`#`, `**`, `-`)

Output directory: `notebooks/09-pipeline-validation/` with subdirs `generated_metadata/`, `radio_bulletins/`, `tts_texts/`, `audio/`

#### 2. OCR artefact cleanup (`_clean_ocr` in `step2_scripts.py`)

**Problem:** Step 1 GPU vision inference sometimes emits placeholder lines like `[HEADER BLOCK]`, `[Logo - PAGASA]`, `[Signature/Stamp placeholder]` for parts of the PDF it cannot read clearly. When these reach Step 2, the LLM interprets the whole document as a template and produces bracket-filled placeholder output instead of real bulletin content.

**Fix:** Added `_clean_ocr()` preprocessing:

```python
def _clean_ocr(text: str) -> str:
    # Remove lines that consist entirely of a [BRACKET LABEL]
    text = re.sub(r"^\s*\[[^\]\n]+\]\s*$", "", text, flags=re.MULTILINE)
    # Collapse blank lines left by removals
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
```

Applied to `ocr.md` before every Step 2 LLM call. Also strips `<think>...</think>` blocks that occasionally appear in Ollama responses.

#### 3. `force` flag propagated in Step 1

The `force` parameter in `Step1OCR.run()` now correctly propagates to all three sub-steps (OCR, chart extraction, metadata generation). Previously only the outer `if ... and not force` guard was checked; the individual sub-step checks still used `if not path.exists()` — so `--force` would skip regenerating individual outputs that already existed.

#### 4. Schema validation test suite

`tests/test_schema_validation.py` — 8 unit tests covering `PAGASA_JSON_SCHEMA` validation:

- Valid minimal metadata passes without error
- Missing required fields are caught correctly
- Invalid enum values (bad bulletin type, bad storm category) are rejected
- Null values accepted where schema allows
- Confidence field bounds (0.0–1.0) enforced

### Files changed

| File | Change |
|---|---|
| `notebooks/09-pipeline-validation.ipynb` | New — end-to-end pipeline validation notebook |
| `modal_etl/step2_scripts.py` | `_clean_ocr()` preprocessing; `<think>` block stripping in `_call_ollama_chat()` |
| `modal_etl/step1_ocr.py` | `force` flag correctly propagated to all three sub-steps |
| `tests/test_schema_validation.py` | New — 8 tests for `PAGASA_JSON_SCHEMA` validation |
| `notebooks/08-mms-tts-experiment.ipynb` | Metadata-first radio script experiment cells added |
| `docs/superpowers/plans/2026-04-25-metadata-first-radio-scripts.md` | Implementation plan for metadata-first Step 2 (future modal_etl integration) |

---

## PR #17 — Bug Fixes: Script Language Race Condition + --stem ETL Option
**Date:** 2026-04-25
**Branch:** `feature/bug-fixes-script-lang-stem`
**PR:** jaeyow/weatherspeak-ph#17
**Status:** Complete ✅

### What we fixed

#### 1. Script language race condition in `BulletinAudioSection`

**Problem:** When navigating to a storm page with a saved language preference (e.g. EN), the "Read Bulletin" text would sometimes display Cebuano instead of English.

**Root cause:** `BulletinAudioSection` initialises with `language = 'ceb'` and reads `localStorage` in a `useEffect`. Both the initial CEB fetch and the corrected EN fetch run concurrently. If the CEB response resolves after the EN response (e.g. CEB was already in-flight when the language updated), it overwrites `scriptText` with CEB content.

**Fix:** Added a `cancelled` flag to the script fetch `useEffect`. When the effect reruns (because `language` changed), the cleanup function sets `cancelled = true`, preventing the stale CEB response from calling `setScriptText`.

```tsx
// Before
fetch(audioUrl(current.script_path))
  .then(r => r.text())
  .then(text => setScriptText(text))
  .catch(() => setScriptText(null))
  .finally(() => setScriptLoading(false));

// After
let cancelled = false;
fetch(audioUrl(current.script_path))
  .then(r => r.text())
  .then(text => { if (!cancelled) setScriptText(text); })
  .catch(() => { if (!cancelled) setScriptText(null); })
  .finally(() => { if (!cancelled) setScriptLoading(false); });
return () => { cancelled = true; };
```

#### 2. `--stem` option for targeted ETL re-runs

**Problem:** No way to re-run the ETL for a single specific bulletin (e.g. to fix an empty CEB script or a wrong audio duration) without modifying code or waiting for a full batch run.

**Fix:** Added `--stem` option to `run_batch.py`. When provided, the pipeline runs for exactly that one bulletin instead of fetching the newest N events.

```bash
uv run modal run modal_etl/run_batch.py --stem "PAGASA_25-TC22_Verbena_TCB#24" --force
```

Backed by a new `get_bulletin_by_stem(stem)` function in `bulletin_selector.py` that looks up the matching entry from the GitHub archive (raises `ValueError` if not found).

#### 3. `.playwright-mcp/` added to `.gitignore`

Playwright MCP session artifacts (screenshots, snapshots, console logs) were not gitignored. Added `.playwright-mcp/` to `.gitignore`.

### Files changed

| File | Change |
|---|---|
| `web/components/BulletinAudioSection.tsx` | `cancelled` flag in script fetch effect to prevent stale response overwrite |
| `modal_etl/run_batch.py` | `--stem` option; uses `get_bulletin_by_stem()` when provided |
| `modal_etl/bulletin_selector.py` | New `get_bulletin_by_stem(stem)` function |
| `CLAUDE.md` | Document `--stem --force` ETL invocation in ETL Operations section |
| `.gitignore` | Add `.playwright-mcp/` |

---

## PR #16 — Bulletin PDF Preview Accordion + Responsive Layout
**Date:** 2026-04-23
**Branch:** `feature/multi-bulletin-history`
**Status:** Complete ✅

### What we built

Improved the bulletin viewing experience with collapsible PDF previews and responsive layout. Historical bulletins now display page 1 preview inline instead of forcing downloads, and the layout adapts to desktop screen sizes.

### Key Features

#### 1. Historical Bulletin PDF Preview Accordion

Created `BulletinHistoryAccordion` component that replaces the old link-based bulletin history:

**User Experience:**
- Click a bulletin number → accordion expands showing page 1 PDF preview
- Only one bulletin expanded at a time (auto-closes others)
- "Download Full PDF" button available when expanded
- Click again to collapse
- No unwanted downloads — everything stays in-browser

**Technical:**
- Uses `react-pdf` + `pdfjs-dist` for client-side PDF rendering
- Renders only page 1 (no need to download full PDF)
- Loading spinner while PDF loads from PAGASA servers
- Error handling for failed PDF loads
- Responsive width (max 800px, adapts to screen size)
- Removed inaccurate date/time display (bulletins show number only)

#### 2. Collapsible Storm Track Chart

Created `LatestBulletinSection` component for the latest bulletin's storm track:

- Starts expanded by default
- Chevron icon indicates expand/collapse state
- Click "STORM TRACK" header to toggle visibility
- Shows extracted chart image (PNG from ETL Step 1)
- Smooth animations matching accordion style

#### 3. Responsive Layout

Fixed narrow desktop layout issue:

**Before:** `max-w-lg` (512px) on all screens — app appeared in narrow band on desktop  
**After:** Responsive widths:
- 📱 Mobile (< 768px): 512px max (unchanged)
- 📱 Tablet (768px+): 672px max (`md:max-w-2xl`)
- 💻 Desktop (1024px+): 896px max (`lg:max-w-4xl`)

#### 4. Mock Data SQL Scripts

Added local testing utilities in `supabase/migrations/`:
- `mock_active_storm.sql` — insert a mock active typhoon with Signal 3
- `mock_active_storm_simple.sql` — simpler version with fewer fields
- `debug_mock_storm.sql` — diagnostic queries to verify data

Enables frontend development without running full ETL pipeline.

### Files changed

| File | Change |
|---|---|
| `web/package.json` | Added `react-pdf@^9.2.0`, `pdfjs-dist@^4.0.379` |
| `web/components/BulletinHistoryAccordion.tsx` | New — PDF preview accordion for historical bulletins |
| `web/components/LatestBulletinSection.tsx` | New — collapsible storm track chart display |
| `web/app/storms/[stormId]/page.tsx` | Use new accordion and latest bulletin section components |
| `web/app/layout.tsx` | Responsive max-width (`max-w-lg md:max-w-2xl lg:max-w-4xl`) |
| `supabase/migrations/mock_active_storm.sql` | New — mock active storm data for local testing |
| `supabase/migrations/mock_active_storm_simple.sql` | New — simplified mock data script |
| `supabase/migrations/debug_mock_storm.sql` | New — diagnostic queries for troubleshooting |

### Technical Decisions

**Why react-pdf over iframe/embed:**
- Better control over loading states and errors
- Can render specific pages only (page 1 preview)
- Responsive sizing without scroll bars
- Works with CORS from PAGASA servers

**Why remove date/time from historical bulletins:**
- Dates are inferred via 6-hour intervals (not OCR'd from PDF)
- Inaccurate timestamps confuse users
- Bulletin number alone is sufficient identifier

**Why accordion over modal:**
- Faster interaction (no navigation)
- Mobile-friendly (no overlay management)
- Consistent with collapsible design pattern throughout app

### Next Steps

- Backend: Full bulletin history backfill (PR #15 Phase II)
- Frontend: Storm summary audio player (Mode 2)
- UX: Add loading skeletons for slow PDF loads

---

## PR #15 — Multi-Bulletin History Discovery
**Date:** 2026-04-23
**Branch:** `feature/multi-bulletin-history`
**Status:** Complete ✅

### What we built

Automatic discovery and registration of all historical bulletins for each storm processed by the ETL pipeline. When WeatherSpeak processes the latest bulletin for a storm (e.g. Basyang #23), it now discovers and registers bulletins #1–#22 as lightweight database rows, making the full bulletin history visible in the web UI.

**Key constraint:** Only the latest bulletin receives full WeatherSpeak treatment (OCR + translations + audio synthesis). Historical bulletins are registered with minimal metadata and link directly to the original PAGASA PDF.

### Architecture

After Step 4 (Supabase upload) completes successfully, a discovery pass runs:

1. Query GitHub archive API for ALL bulletins matching the storm's `storm_id` and `event_name`
2. Filter out the latest bulletin (already processed)
3. Infer `issued_at` timestamp for each historical bulletin using 6-hour intervals
4. Upsert lightweight `bulletins` rows (no `bulletin_media` rows)

The web UI distinguishes full-treatment bulletins (have `bulletin_media` rows) from historical bulletins (no `bulletin_media`) — full bulletins link to `/bulletins/[id]`, historical bulletins link directly to `pdf_url`.

### Implementation

**`modal_etl/bulletin_selector.py`** — new function:
```python
def get_all_bulletins_for_storm(storm_id: str, event_name: str) -> list[BulletinInfo]
```
- Queries GitHub archive API (same as `get_latest_bulletins`)
- Filters to bulletins matching both `storm_id` and `event_name`
- Returns all bulletins sorted by `bulletin_seq` ascending (oldest first)
- Fills `pdf_url` for each entry

**`modal_etl/step4_upload.py`** — discovery pass:
- `_infer_issued_at()` — estimates issued timestamp via 6-hour intervals from latest bulletin
- `_discover_historical_bulletins()` — queries archive, infers dates, upserts lightweight `bulletins` rows
- Called automatically at the end of `step4_upload()` after successful upload
- Best-effort — failure does not abort the main bulletin upload

**Schema unchanged** — the existing `bulletins` table already supports lightweight rows:
- Historical bulletins: `storm_id`, `stem`, `bulletin_type`, `bulletin_number`, `pdf_url`, `issued_at` (inferred)
- All other columns (`category`, `wind_signal`, position data, etc.) remain NULL
- No `bulletin_media` rows created

### Testing

**`tests/test_bulletin_selector.py`** — 5 new tests for `get_all_bulletins_for_storm`:
- Returns all bulletins for a storm event
- Sorted by `bulletin_seq` ascending
- Excludes bulletins from other storms
- PDF URLs properly encoded
- Returns empty list for unknown storm

All 70 tests passing.

### Example

Processing `PAGASA_26-TC02_Basyang_TCB#23` (latest bulletin for Typhoon Basyang):
- **Full treatment:** Bulletin #23 gets OCR, 3 radio scripts, 3 audio files, chart extraction
- **Discovery pass:** Bulletins #1–#22 discovered and registered with inferred `issued_at` timestamps
- **Web UI:** Storm page shows all 23 bulletins; only #23 has audio playback; #1–#22 link to PAGASA PDF

### Design spec

[docs/superpowers/specs/2026-04-23-multi-bulletin-history-design.md](docs/superpowers/specs/2026-04-23-multi-bulletin-history-design.md)

### Files changed

| File | Change |
|---|---|
| `modal_etl/bulletin_selector.py` | New `get_all_bulletins_for_storm()` function |
| `modal_etl/step4_upload.py` | `_infer_issued_at()`, `_discover_historical_bulletins()` helpers; discovery pass called after upload |
| `tests/test_bulletin_selector.py` | 5 new tests for historical bulletin discovery |

### Next steps

**Phase II (future):** Full backfill — run OCR on all historical bulletins and generate a single "storm summary" audio that covers the entire lifecycle of the storm. Design notes documented in the spec and `memory://project_phase2_storm_summary.md`.

---

## PR #14 — TTS Prompt Improvements
**Date:** 2026-04-22
**Branch:** `feature/tts-prompt-improvements`

### What we did

A focused pass to improve the quality and correctness of every prompt in the Step 2 pipeline, and to add two new post-processing LLM passes for TL and CEB.

#### 1. Clarified the two-prompt architecture

The pipeline produces two distinct outputs per language that serve different purposes:

- **`radio_{lang}.md`** — displayed on the website for humans to read. Must use natural, readable language. No phonetic spellings.
- **`tts_{lang}.txt`** — fed directly to the TTS engine. Must use phonetic spellings so the synthesiser pronounces words correctly.

Previously `_RADIO_PROMPTS` incorrectly included phonetic spelling lists (e.g. `kai-lo-me-tros`, `tro-pi-kal di-pre-syon`). These were stripped out and replaced with natural-language Tagalog/Cebuano equivalents.

#### 2. Rewrote `_RADIO_PROMPTS` — purpose-driven, conversational, 200 words

All three language prompts now open with a **PURPOSE** statement explaining who will hear this and why conciseness matters. They include an explicit **priority order**:

1. Storm name + category
2. Location + track
3. Affected areas + Signal levels
4. What to do (evacuate, stay indoors, avoid coast)
5. Next update time

Word limit tightened from ~300 to **no more than 200 words**. TL and CEB prompts now use natural-language weather vocabulary (bagyo, kusog nga balud, paglikas) instead of phonetics.

#### 3. Added two new Gemma 4 cleanup passes (TL + CEB only)

After the initial TTS text generation, two additional LLM calls run sequentially:

- **Pass 2 — English word cleanup** (`_cleanup_english_words`): finds any English words that slipped through and replaces them with Tagalog/Cebuano equivalents or phonetically spelled forms.
- **Pass 3 — Number conversion** (`_cleanup_numbers`): converts all remaining digit numbers to spoken words using the Spanish-borrowed system (CEB: baynte uno, isyento treynta / TL: beinte uno, isang daan treynta).

Both passes are also added as separate cells in notebook 08 for local testing.

#### 4. Fixed reversed number lookup tables

The `_TTS_PROMPTS` number tables were written as `singko=5` (word→digit) when they should read `5=singko` (digit→word). Fixed in `step2_scripts.py`, notebook 06, and notebook 08.

#### 5. Fixed key inconsistency between notebooks

Notebook 08 used `"user_template"` as the prompt key while `step2_scripts.py` used `"user"`. Standardised to `"user"` in notebook 08 and `"user_template"` in notebook 06 (to match existing `build_user_prompt()` function).

#### 6. Notebooks synced from ETL script

`notebooks/06-radio-bulletin.ipynb` and `notebooks/08-mms-tts-experiment.ipynb` updated to match all prompt changes in `step2_scripts.py`.

### Files changed

| File | Change |
|---|---|
| `modal_etl/step2_scripts.py` | `_RADIO_PROMPTS` rewritten (purpose, priority order, 200 words, no phonetics); `_CLEANUP_PROMPTS` + `_NUMBER_CLEANUP_PROMPTS` added; `_cleanup_english_words()` + `_cleanup_numbers()` helpers added; both called in `step2_scripts()` |
| `notebooks/06-radio-bulletin.ipynb` | `PROMPTS` synced from ETL; `TTS_PROMPTS` synced from notebook 08 |
| `notebooks/08-mms-tts-experiment.ipynb` | English cleanup cell added; number conversion cell added; sentence dump cell added; `user_template` → `user` key fix |
| `README.md` | Step 2 description updated to reflect 3-pass pipeline |

---

## PR #0 — Project Kickoff & Planning
**Date:** 2026-04-10  
**Branch:** `main` (initial commit)  
**Commit:** `ced18fe`

### What we did
- Defined the project concept: **WeatherSpeak PH** — AI-powered multilingual severe weather communications for the Philippines
- Identified the core problem: PAGASA issues typhoon bulletins in English only, leaving 74+ Filipino language communities underserved during disasters
- Designed the full technical architecture:
  - PDF ingestion and parsing (pdfplumber / PyPDF2)
  - Gemma 4 (26B/31B) for translation and multimodal bulletin map understanding
  - Deployment: Gemma 4 served via **Ollama on Modal** (serverless GPU)
  - Google Cloud TTS for audio generation (Tagalog native, Bisaya fallback)
  - Mobile-first PWA frontend (Next.js / Vercel)
  - Supabase/PostgreSQL for bulletin storage
- Selected hackathon tracks:
  - **Impact Track — Digital Equity & Inclusivity** ($10k)
  - **Impact Track — Global Resilience** ($10k)
  - **Special Technology Track — Ollama** ($10k)
  - **Main Track** (grand prize contender)
- Scoped the implementation roadmap across 5 weeks (Apr 10 – May 18)
- Created `.gitignore` and committed `HACKATHON_PLAN.md`
- Created public GitHub repo: [jaeyow/weatherspeak-ph](https://github.com/jaeyow/weatherspeak-ph)

### Key decisions
- Focus on 2 dialects for hackathon: Tagalog + Bisaya/Cebuano
- Two processing modes: Mode 1 (latest bulletin translation) and Mode 2 (full storm narrative synthesis — stretch goal)
- Multimodal: use Gemma 4 vision to interpret storm track maps embedded in PDF bulletins
- Dropped Unsloth track — no LLM fine-tuning in scope; using Filipino TTS to read Bisaya text as an acceptable Phase 1 fallback
- Server-side inference only (no offline/edge deployment)

---

## PR #1 — OCR Notebook Experiments
**Date:** 2026-04-10  
**Branch:** `feature/ocr-experiments`  
**Status:** Ready for execution

### Goals
- Research and compare modern open-source OCR solutions (2025-2026 state of the art)
- Test traditional OCR vs Gemma 4 vision-based text extraction
- Evaluate text extraction quality on real PAGASA bulletin PDFs
- Identify structure of bulletins: storm name, category, wind speed, warnings, affected areas, coordinates
- Determine best approach for production pipeline

### Implementation Complete ✅

Created 5 Jupyter notebooks in `notebooks/` directory:

1. **01-ocr-setup-and-data.ipynb** - Setup and data collection
   - Clones pagasa-parser/bulletin-archive GitHub repo
   - Selects 10 diverse sample bulletins
   - Converts PDFs to images (200 DPI)
   - Creates evaluation framework

2. **02-surya-ocr.ipynb** - Surya OCR testing
   - Tests best AI-native OCR (19.6k stars)
   - Benchmarks processing speed and accuracy
   - Built for document understanding

3. **03-paddleocr.ipynb** - PaddleOCR testing
   - Tests best traditional deep learning OCR (75k+ stars)
   - Production-grade baseline
   - Confidence scores for quality assessment

4. **04-gemma4.ipynb** - Gemma 4 Vision testing (CRITICAL)
   - Tests Gemma 4 26B via Ollama locally
   - Zero-shot document extraction
   - Hypothesis: Can vision-first replace specialized OCR?

5. **05-comparison.ipynb** - Comprehensive comparison
   - Side-by-side analysis of all three approaches
   - Decision matrix with weighted scores
   - Production architecture recommendation

### Decision Framework

**Scenario A**: Gemma 4 Vision accuracy ≥ 90% → Vision-first pipeline  
**Scenario B**: Gemma 4 Vision accuracy 70-90% → Hybrid (OCR + Gemma 4)  
**Scenario C**: Gemma 4 Vision accuracy < 70% → Pure OCR pipeline  

### Next Actions

1. Run notebook 01 to download PAGASA bulletins and prepare test data
2. Execute notebooks 02-04 to gather OCR results from all three approaches
3. Perform manual visual assessment in notebook 05
4. Update decision matrix with scores based on inspection
5. Calculate weighted totals and choose production scenario
6. Update HACKATHON_PLAN.md with chosen architecture
7. Begin Week 2 implementation (blocked until OCR decision made)

### OCR Research Plan

### OCR Research Plan — Simplified

We'll benchmark **3 approaches** on PAGASA PDFs:

#### 1. **Surya OCR** (Best AI-Native OCR)
- 19.6k stars, actively maintained
- Beats Google Cloud Vision on benchmarks
- 90+ languages, built for document analysis
- Layout detection + table recognition included
- `pip install surya-ocr`

#### 2. **PaddleOCR** (Best Traditional Deep Learning OCR)
- 75k+ stars, production-grade
- 100+ languages, industrial strength
- Most mature and actively maintained (updated 3 days ago)
- PP-Structure for layout analysis
- Widely used in production

#### 3. **Gemma 4 Vision** (Hypothesis: Vision-First Approach)
- E2B or E4B multimodal models
- Zero-shot document extraction
- Can understand structure semantically
- Same model for OCR + translation
- **Key question**: Can VLM replace specialized OCR for structured government docs?

### Why These Three?

**Surya** = Current SOTA for open-source document OCR  
**PaddleOCR** = Battle-tested production baseline  
**Gemma 4** = Novel vision-first approach (aligns with hackathon theme)

If Gemma 4 Vision performs well, we simplify the entire pipeline. If not, we have two proven fallbacks.

#### Evaluation Metrics
For each approach, measure:
- **Accuracy**: Character/word error rate vs manual ground truth
- **Completeness**: Did it extract all sections (storm name, coordinates, warnings, affected areas)?
- **Structure preservation**: Tables, lists, formatting
- **Speed**: Processing time per page
- **Cost**: API costs (if applicable) or compute requirements
- **Robustness**: Handles scanned vs native PDFs, image quality variations

#### Test Dataset
- Download 10-15 sample PAGASA bulletins from `pagasa-parser/bulletin-archive`
- Include variety:
  - Different storms (recent typhoons)
  - Different bulletin types (SWB, TCB, TCA)
  - Sequential bulletins (#01, #05, #10, #FINAL)
  - Different formats/layouts if any

#### Notebooks to Create
1. `01-ocr-setup-and-data.ipynb` - Setup, download sample PAGASA PDFs, define evaluation metrics
2. `02-surya-ocr.ipynb` - Test Surya OCR (best AI-native)
3. `03-paddleocr.ipynb` - Test PaddleOCR (best traditional)
4. `04-gemma4.ipynb` - Test Gemma 4 Vision (hypothesis)
5. `05-comparison.ipynb` - Side-by-side comparison, decision matrix

### Evaluation Metrics
For each approach, measure:
- **Accuracy**: Text extraction correctness (manual spot-checks on 10 bulletins)
- **Structure**: Can it extract storm name, category, coordinates, warnings, affected areas?
- **Tables**: Does it handle coordinate tables, wind speed tables?
- **Speed**: Processing time per page
- **Cost/Complexity**: Setup effort, dependencies, compute requirements
- **Integration**: How easy to integrate with translation pipeline?

### Expected Outcome
**Scenario A**: Gemma 4 Vision works well → Use vision-first pipeline (OCR + translation in one model)  
**Scenario B**: Gemma 4 needs help → Hybrid (Surya/PaddleOCR for text + Gemma 4 for translation)  
**Scenario C**: Gemma 4 struggles → Pure OCR pipeline (Surya or PaddleOCR → Gemma 4 translation)

By testing these 3, we'll know which path to take for production.
- Produce structured JSON output from a sample bulletin

---

## PR #2 — Replace PaddleOCR with Marker
**Date:** 2026-04-11  
**Branch:** `feature/ocr-experiments`  
**Status:** In progress

### What changed

PaddleOCR was dropped from the experiment suite due to persistent macOS compatibility issues:
- `PaddleOCR()` initialization causes a hard **kernel crash** in Jupyter on macOS (x86_64, Python 3.12)
- PaddlePaddle 3.0.0 has known segfault issues on macOS — a native C++ dependency problem, not a code issue
- No straightforward fix without downgrading Python or switching platforms

**Replaced `03-paddleocr.ipynb` with `03-marker.ipynb`** using [Marker](https://github.com/VikParuchuri/marker).

### Why Marker

PAGASA bulletins contain both **text and a storm track chart**. Traditional text-only OCR tools (EasyOCR, Tesseract, PaddleOCR) would ignore the chart entirely. Marker is the only open-source traditional pipeline tool that handles mixed content:

| Tool | Text | Tables | Charts/Figures |
|---|---|---|---|
| Surya | ✅ | ✅ | ❌ |
| EasyOCR / Tesseract | ✅ | ❌ | ❌ |
| **Marker** | ✅ | ✅ | ✅ (saves as image) |
| Gemma 4 Vision | ✅ | ✅ | ✅ (understands semantically) |

Marker sits on top of Surya for OCR, adds layout analysis, and outputs clean **Markdown** — a better format for downstream LLM translation than raw text.

### Key decisions

- Traditional OCR baseline is now Marker, not PaddleOCR
- Decision framework updated: Scenario B/C fallback is "Surya or Marker", not "Surya or PaddleOCR"
- Model name in notebook 04 corrected from `gemma2:27b-vision` → `gemma4:26b` → `gemma4:e4b`
- Switched to `gemma4:e4b` for local inference: good enough accuracy with significantly lower latency than 26B

### What this changes about the comparison narrative

Marker's chart extraction (image only, no understanding) vs Gemma 4 Vision's chart *comprehension* is now a stronger demonstration of the vision-first advantage. The story becomes: traditional tools can *find* the storm track chart, but only Gemma 4 can *read* it.

---

## PR #3 — Switch to Gemma 4 E4B for Local Inference
**Date:** 2026-04-12  
**Branch:** `feature/ocr-experiments`  
**Status:** In progress

### What changed

Switched the vision model in notebook 04 from `gemma4:26b` to `gemma4:e4b`.

### Why E4B

- **Latency**: 26B takes 80–1200s per sample locally; E4B is significantly faster on the same hardware
- **Accuracy**: E4B accuracy on structured document extraction is good enough for PAGASA bulletins
- **Local-first**: No cost implications — all inference runs via Ollama locally, so model size only affects speed
- **Pragmatic**: For a hackathon demo pipeline processing 10 bulletins, E4B hits the right speed/quality tradeoff

### Other improvements in this session

- **Incremental save**: Processing loop now saves markdown and structured JSON to disk after each sample instead of batching everything in memory. Safe to interrupt mid-run; scales to any number of files.
- **Constrained decoding**: Step 2 now passes the full `PAGASA_JSON_SCHEMA` to Ollama's `format` field instead of `"json"` string — guarantees schema-valid output token-by-token, eliminating JSON parse failures.
- **Cleaner result dict**: `markdown`, `full_text`, and `raw_step2` removed from the in-memory summary. Markdown is on disk as `.md`; structured JSON is in `structured/`; summary JSON contains only timing/metadata.

---

## PR #4 — OCR Decision: Scenario A (Vision-First)
**Date:** 2026-04-12  
**Branch:** `feature/ocr-experiments`  
**Status:** Complete ✅

### Decision

**Gemma 4 E4B Vision is the chosen production approach — Scenario A.**

After running all three OCR experiments (Surya, Marker, Gemma 4 E4B) across 10 PAGASA bulletin samples and completing the comparison in notebook 05, Gemma 4 Vision passed with good enough accuracy.

### Why Gemma 4 wins

- **Accuracy**: Good enough on structured PAGASA bulletin text
- **Chart comprehension**: Only Gemma 4 can *semantically interpret* the storm track map — Surya ignores it entirely, Marker extracts it as a raw image with no understanding
- **Pipeline simplicity**: One model handles OCR + translation — no separate OCR engine to maintain
- **Hackathon alignment**: Gemma 4 throughout the entire stack

### Production pipeline (Scenario A)

```
PAGASA PDF → image → Gemma 4 E4B (Step 1: OCR → markdown)
                   → Gemma 4 E4B (Step 2: markdown → structured JSON)
                   → Gemma 4 E4B (Step 3: translation to Tagalog/Bisaya)
                   → Google Cloud TTS → audio
```

### What this unblocks

- Translation pipeline design (Week 2)
- TTS integration strategy
- Geographic context features
- Database schema for bulletin storage

---

## PR #5 — Radio Bulletin Generator (3 Languages, Markdown Output)
**Date:** 2026-04-12
**Branch:** `feature/radio-bulletin`
**Status:** In progress

### What we built

`06-radio-bulletin.ipynb` — generates ~750-word (~5 minute) radio broadcast scripts in **English, Tagalog, and Cebuano** from PAGASA bulletin markdown. Produces 6 scripts total (2 bulletins × 3 languages).

### Approach

- **Input**: Raw markdown from notebook 04 (not structured JSON — markdown carries the full bulletin text and is a better source for prose generation)
- **Model**: Gemma 4 E4B via Ollama (text-only — no vision needed here)
- **Output**: Markdown files saved to `data/radio_bulletins/{stem}_radio_{lang}.md`
- **Review cell**: uses `IPython.display.Markdown` to render scripts with full formatting in the notebook — headings, bold storm names, and section structure display correctly rather than printing raw markdown syntax

### Radio style rules baked into each language prompt

- Flowing prose suitable for reading aloud
- Numbers spelled out for spoken delivery ("one hundred thirty kilometres per hour")
- Storm name and signal numbers bolded on first mention per section; repeated at least twice for mid-tune-in listeners
- Structured with Markdown headings: title → Current Situation → Forecast Track → Affected Areas → Public Safety Advisory → Closing
- Targets ~150 wpm (standard broadcast pace) for 5-minute read
- Word count strips Markdown syntax before estimating spoken duration

### Scope

Working on 2 bulletins:
- `PAGASA_20-19W_Pepito_SWB#01` — Severe Weather Bulletin, Tropical Depression Pepito
- `PAGASA_22-TC02_Basyang_TCA#01` — Tropical Cyclone Alert, Basyang

### Next steps

- Run notebook and validate script quality against actual PAGASA bulletin language
- Feed English output into Google Cloud TTS pipeline
- Evaluate Tagalog/Cebuano output with native speakers

---

## PR #6 — TTS Experiment: Coqui XTTS v2 → MP3
**Date:** 2026-04-14
**Branch:** `feature/tts-experiment`
**Status:** Complete ✅

### What we built

`07-tts-experiment.ipynb` — synthesizes radio bulletin scripts into MP3 audio using **Coqui XTTS v2**. Proven end-to-end: markdown → plain text → chunked synthesis → MP3.

### Approach

- **Model**: Coqui XTTS v2 (`tts_models/multilingual/multi-dataset/xtts_v2`)
- **Speaker**: `"Damien Black"` — built-in male voice, authoritative broadcast tone
- **Language mapping**: `en→en` (native), `tl→es` (Spanish phoneme approximation), `ceb→es` (same)
- **No intermediate WAV**: numpy array → pydub `AudioSegment` → MP3 at 128kbps directly in memory
- **Chunking**: XTTS v2 has a ~200-char synthesis limit; long scripts are split on sentence boundaries, arrays concatenated before export
- **Preprocessing**: multi-pass markdown stripper that removes stage directions (`**(Sound effect:...)**`), role labels (`**BROADCASTER:**`, `**Boses:**`), headings converted to plain spoken sentences, list markers stripped — nothing in the text that shouldn't be read aloud

### Key decisions

- Spanish phoneme (`es`) for Tagalog/Cebuano: Filipino shares the same 5-vowel system and consonant inventory as Spanish — significantly better than English mode for Filipino words
- Community Coqui Tagalog model (`tts_models/tl/...`) noted as a future alternative — trade-off is native phoneme accuracy vs. inconsistent voice
- Functions (`preprocess_for_tts`, `synthesize_to_mp3`) are **Modal-ready**: pure inputs (str, Path), no notebook globals — designed for direct extraction to `@app.function`
- `COQUI_TOS_AGREED=1` env var set in notebook to bypass interactive license prompt in Jupyter

### Infrastructure

- Added `coqui-tts>=0.25.0`, `pydub>=0.25.1`, `numpy>=1.26.0` to `pyproject.toml`
- `transformers>=4.43.0,<=4.46.2` pinned for coqui-tts 0.25.x compatibility
- `tests/test_tts_preprocess.py` — 9 unit tests for the preprocessing function (includes regression test for `***` horizontal rule / bold interaction bug caught in code review)
- Added `CLAUDE.md` — project context auto-loads every Claude Code session, no more manual init needed
- Design spec: `docs/superpowers/specs/2026-04-13-tts-experiment-design.md`
- Implementation plan: `docs/superpowers/plans/2026-04-13-notebook-07-tts-experiment.md`

### Audio quality notes

- Output quality is acceptable for an experiment — XTTS v2 on CPU is slow (~500s per bulletin file)
- Spanish phoneme for Tagalog/Cebuano produces intelligible output; not native-quality
- TTS quality is a known limitation for Phase 1; Google Cloud TTS (already planned) will replace this in production
- Tested on `PAGASA_20-19W_Pepito_SWB#01_radio_ceb.md` — intermediate plain text saved alongside MP3 for inspection

### Next steps

- Evaluate Google Cloud TTS for Tagalog (native support) as production replacement
- Deploy Step 3 (TTS) to Modal alongside Steps 1–2
- Wire up full ETL pipeline trigger (PAGASA bulletin detection TBD)

---

## PR #7 — TTS Experiment: Facebook MMS TTS + SpeechT5 (All 3 Languages)
**Date:** 2026-04-15
**Branch:** `feature/tts-experiment`
**Commit:** `03538c5`
**Status:** In progress

### What we built

`08-mms-tts-experiment.ipynb` — evaluates **Facebook MMS TTS** as a replacement for Coqui XTTS v2. Key motivation: MMS provides native Cebuano and Tagalog models, eliminating the Spanish phoneme approximation hack from PR #6.

### Models used

| Language | Model | Notes |
|---|---|---|
| Cebuano | `facebook/mms-tts-ceb` (VITS, 36.3M) | Native phonemes |
| Tagalog | `facebook/mms-tts-tgl` (VITS, 36.3M) | Native phonemes |
| English | `microsoft/speecht5_tts` | Better than `facebook/mms-tts-eng` |

### Approach

- **Sentence-level synthesis**: each sentence synthesised separately, then silence-stitched via pydub into a single MP3
- **Silence stitching**: 250ms between sentences, 400ms at paragraph boundaries (CEB/TL); 300ms/500ms (EN)
- **Speech speed**: 1.15× for Cebuano/Tagalog to match news bulletin pace; English at 1.0×
- **Auto-generate missing TTS text**: if `_tts_{lang}.txt` doesn't exist, Gemma 4 E4B generates it from the radio markdown — keeps the pipeline self-contained

### SpeechT5 bug fixed: silent English MP3

The initial English MP3 was full silence (but had proper filesize). Root cause: the synthesis function treated SpeechT5 as a VITS model — calling `model(**inputs).waveform` which produced NaN values without speaker embeddings. Fix required three changes:

1. Load `SpeechT5HifiGan` vocoder (`microsoft/speecht5_hifigan`) — VITS outputs waveforms directly; SpeechT5 outputs mel-spectrograms that must be vocoded
2. Provide speaker embeddings (random 512-dim tensor — dataset loading had a compatibility issue with newer `datasets` library)
3. Use `model.generate_speech(input_ids, speaker_embeddings)` → vocoder path instead of `model(**inputs).waveform`

### Language-specific sentence preparation

VITS models (MMS) require lowercase, punctuation-stripped input. SpeechT5 handles normal English better. Split into two functions:

- `prepare_mms_sentences()` — lowercase, strip punctuation (CEB/TL)
- `prepare_english_sentences()` — preserve capitalisation and punctuation (EN)

English now benefits from proper prosody at sentence boundaries (comma pauses, question inflection, etc.) because punctuation context is preserved.

### Pacing improvements

Added `speech_speed` parameter to `synthesize_with_mms()`. Uses pydub `speedup()` for post-synthesis time-stretching. Per-language config dict makes it easy to tweak without touching the synthesis function:

```python
synthesis_config = {
    "ceb": {"sentence_pause_ms": 250, "paragraph_pause_ms": 400, "speech_speed": 1.15},
    "tl":  {"sentence_pause_ms": 250, "paragraph_pause_ms": 400, "speech_speed": 1.15},
    "en":  {"sentence_pause_ms": 300, "paragraph_pause_ms": 500, "speech_speed": 1.0},
}
```

### MMS vs XTTS v2 comparison

| Model | Lang | Synthesis time | Audio duration | Model size |
|---|---|---|---|---|
| MMS | Cebuano | ~42s | ~6 min | ~140 MB |
| MMS | Tagalog | ~36s | ~5.6 min | ~140 MB |
| MMS + SpeechT5 | English | ~66s | ~3.3 min | ~200 MB |
| XTTS v2 | Cebuano | 821s | 7.8 min | 1.87 GB |

MMS is **~20× faster** for Cebuano and uses **4× less storage** across all three languages combined vs XTTS v2 alone.

### Key decisions

- SpeechT5 replaces `facebook/mms-tts-eng` for English: measurably better pronunciation, handles proper nouns and punctuation naturally
- Random speaker embedding is acceptable for now; a named speaker from CMU Arctic xvectors would give a more consistent voice identity in production
- Speech speed applied as post-processing (pydub) rather than model parameter — keeps the approach model-agnostic and easy to tune per language
- VITS punctuation stripping is a hard model requirement, not a quality choice — documented clearly to avoid future confusion

### Next steps

- Listen and score all 3 MP3s (quality + naturalness rubric in notebook cell 4)
- Decide: replace XTTS v2 with MMS for production, or keep XTTS v2 for higher quality?
- If MMS is chosen: extract `synthesize_with_mms` + `prepare_*_sentences` into a Modal function
- Investigate named speaker embeddings for consistent English voice identity

---

## PR #8 — TTS Pacing & Phonetic Spelling Improvements
**Date:** 2026-04-16
**Branch:** `feature/tts-experiment`
**Status:** Complete ✅

### What we improved

Tuned notebook 08 (`08-mms-tts-experiment.ipynb`) for better audio quality across Cebuano and Tagalog — two areas that were poor after the initial MMS integration:

1. **Speech speed calibrated per language** — the MMS VITS models speak at different natural rates. Tuned separately until each felt right at radio broadcast pace:
   - Cebuano: `1.40×` (was `1.15×` — too slow; `1.5×` was chipmunk territory)
   - Tagalog: `1.35×` (confirmed good at this rate)
   - English (SpeechT5): `1.0×` (already well-paced, untouched)

2. **Tighter silence stitching for CEB/TL** — reduced inter-sentence and paragraph pauses:
   - Sentence pause: `250ms → 150ms`
   - Paragraph pause: `400ms → 250ms`

3. **Phonetic TTS text generation — Cebuano** — rewrote the Gemma 4 prompt in Cebuano (for stricter adherence) with 30+ phonetic mappings covering the English words that were leaking through:
   - `PAGASA → PAG-ASA` (was incorrectly `pa-ga-sa`)
   - `forecast → pore-kast`, `coastal → kos-tal`, `signal → sig-nal`
   - All cardinal directions: `northwest → nor-wes`, `westward → wes-ward`, etc.
   - `first aid kit → pirst eyd kit`, `rescue kit → res-kyuw kit`, `evacuation → i-ba-kyu-we-yon`
   - Hard rule enforced: no English word left unspelled phonetically

4. **Phonetic TTS text generation — Tagalog** — applied the same treatment in Tagalog with language-appropriate phonetic variants (e.g. `evacuation → i-ba-kyu-we-syon`, `station → is-tas-yon`, `province → pro-bins-ya`).

5. **`FORCE_REGEN` mechanism** — added a `FORCE_REGEN = ["ceb"]` list to the text generation cell so specific languages can be re-generated without deleting files or editing the skip logic each time.

### Final synthesis config

```python
synthesis_config = {
    "ceb": {"sentence_pause_ms": 150, "paragraph_pause_ms": 250, "speech_speed": 1.40},
    "tl":  {"sentence_pause_ms": 150, "paragraph_pause_ms": 250, "speech_speed": 1.35},
    "en":  {"sentence_pause_ms": 300, "paragraph_pause_ms": 500, "speech_speed": 1.0},
}
```

### Key decisions

- Speed resampling (frame-rate approach) introduces a small pitch shift at higher multipliers — `1.5×` was audibly chipmunk; `1.40×` is the highest usable value for the CEB VITS voice before quality degrades
- Phonetic guide is written in the target language (Cebuano / Tagalog) inside each system prompt — Gemma 4 follows native-language instructions more strictly than English instructions for this task
- TTS text `.txt` files committed alongside the notebook — they take ~60s each to generate via Gemma 4 and the phonetic rules are stable enough to treat them as build artifacts

### Next steps

- Evaluate the second bulletin (`PAGASA_22-TC02_Basyang_TCA#01`) through the same pipeline
- Consider named speaker embeddings for SpeechT5 (consistent English voice identity)
- Begin Modal deployment: wrap `synthesize_with_mms` + `prepare_*_sentences` in `@app.function`

---

## PR #9 — Modal ETL Pipeline — Complete (Steps 1–4 + Supabase)
**Date:** 2026-04-17 / 2026-04-18
**Branch:** `feature/modal-etl`
**PR:** jaeyow/weatherspeak-ph#9
**Status:** Complete ✅ — smoke tested end-to-end

### What we built

Full 4-step WeatherSpeak PH ETL pipeline as a batch Modal app. All compute runs on Modal serverless GPU/CPU; Step 4 publishes artifacts to Supabase.

```
pagasa-parser/bulletin-archive (GitHub)
  ↓  bulletin_selector.py

[Local] run_batch.py  ←  @app.local_entrypoint
  ├─► Step1OCR.run.remote(pdf_url)            A10G GPU
  │     Ollama + gemma4:e4b
  │     → ocr.md, chart.png, metadata.json
  ├─► Step2Scripts.run.remote(stem)           A10G GPU
  │     Ollama + gemma4:e4b
  │     → radio_{lang}.md + tts_{lang}.txt × 3
  ├─► Step3TTS.starmap(stem, langs)           A10G GPU × 3 parallel
  │     MMS VITS (CEB/TL) + Coqui XTTS v2 (EN)
  │     → audio_{lang}.mp3 × 3
  └─► Step4Upload.remote(stem)                CPU
        → Supabase Storage (audio + scripts + tts text)
        → Supabase DB (storms, bulletins, bulletin_media)
```

### Key modules

| File | Responsibility |
|---|---|
| `modal_etl/bulletin_selector.py` | GitHub API → newest N events → latest bulletin each |
| `modal_etl/step1_ocr.py` | Gemma 4 E4B OCR → `ocr.md`, `chart.png`, `metadata.json` |
| `modal_etl/step2_scripts.py` | Radio scripts + TTS plain text (EN/TL/CEB) |
| `modal_etl/step3_tts.py` | MMS VITS + Coqui XTTS v2 → MP3 per language |
| `modal_etl/step4_upload.py` | Upload to Supabase Storage + write DB rows |
| `modal_etl/synthesizers/` | `MMSSynthesizer` + `CoquiXTTSSynthesizer` |
| `modal_etl/phonetics.py` | Deterministic phonetic post-processing for TL/CEB |
| `modal_etl/setup_volumes.py` | One-time volume init (Ollama model + TTS weights) |
| `modal_etl/run_batch.py` | Local entrypoint — orchestrates all four steps |
| `supabase/migrations/001_initial_schema.sql` | Full DB schema |

### Key decisions

- **Idempotent + force flag**: every step skips if output exists; `--force` re-runs all steps
- **All steps on GPU**: MMS (CEB/TL) and Coqui XTTS v2 (EN) both explicitly load onto CUDA
- **TTS model swap**: SpeechT5 (scratchy) → Coqui XTTS v2 for English (much better quality)
- **Phonetic post-processing**: `phonetics.py` deterministically converts English terms to phonetic equivalents after Gemma generates TTS text — catches what the LLM misses consistently
- **Strengthened prompts**: radio and TTS prompts for TL/CEB now open with hard "NO ENGLISH" constraint and a 20+ item mandatory phonetic spellings list
- **Storage structure**: flat `{stem}/` folder per bulletin in `weatherspeak-public` bucket; `#` replaced with `_` in storage paths (URL fragment issue)
- **Supabase schema**: `storms` → `bulletins` → `bulletin_media`; `is_active` derived via `storms_with_status` view (no stale flags); all tables public-read, service-role-only write

### Supabase schema

```
storms          (storm_code, storm_name, ...)
  └── bulletins (stem, category, wind_signal, affected_areas jsonb, ...)
        └── bulletin_media (language, audio_path, script_path, tts_path, status)

storms_with_status  VIEW  (is_active derived, current_signal, current_category)
```

### Output per bulletin stem

Modal Volume `/output/{stem}/`: `ocr.md`, `chart.png`, `metadata.json`, `radio_{lang}.md` × 3, `tts_{lang}.txt` × 3, `audio_{lang}.mp3` × 3

Supabase Storage `weatherspeak-public/{stem}/`: `audio_{lang}.mp3` × 3, `radio_{lang}.md` × 3, `tts_{lang}.txt` × 3, `chart.png`

### Bug fixes during smoke test

- `ReadTimeout` in `_wait_for_ollama` — caught alongside `ConnectionError`
- `#` in PDF URL treated as fragment — URL-encoded with `urllib.parse.quote`
- `ARCHIVE_RAW_BASE` pointed to `main` branch — corrected to `master`
- `OLLAMA_TIMEOUT` increased to 600s — vision OCR exceeds 120s per page
- MMS/XTTS running on CPU despite A10G — fixed by installing CUDA torch and calling `.to(device)`
- Stem `%23` URL encoding — decoded in Step 1 and Step 4
- `#` in Supabase Storage paths — replaced with `_`

### Tests

65 unit tests passing across all modules.

### Next steps

- Build Next.js frontend (Vercel, PWA, mobile-first)
- Connect to Supabase for storm listing and audio playback
- Design Lola-first UX: active storm cards → storm page → audio player

---

## PR #11 — Prompt Quality: Low-Literacy Audience + 2-Minute Bulletins
**Date:** 2026-04-19
**Branch:** `main`
**Status:** Complete ✅

### What we improved

Rewrote all Gemma 4 prompts in the ETL pipeline and notebooks to better serve the target audience — Filipinos with low literacy, limited education, and no English background — and shortened the bulletin target from 5 minutes to 2 minutes.

---

#### 1. Bulletin length: 5 minutes → 2 minutes (300 words)

Five-minute bulletins were too long for the target demographic. A clear, direct 2-minute announcement is more likely to be understood and acted upon.

- `notebooks/06-radio-bulletin.ipynb`: `TARGET_WORDS = 750 → 300`, all language references updated (lima ka minuto → duha ka minuto, limang minuto → dalawang minuto)
- All prompts in `_RADIO_PROMPTS` and `_TTS_PROMPTS`: word count target updated to ~300 words / two minutes

#### 2. ETL `_RADIO_PROMPTS` — reframed as formal PAGASA announcement

**Problem:** Prompts framed the model as a "radio broadcaster", causing it to invent station names, radio sign-offs, and placeholders like `[insert program name here]`.

**Fix:** Reframed all three language prompts as a formal PAGASA severe weather announcement. Key changes across EN / TL / CEB:
- Explicit prohibition: no placeholders, no radio show language, no greetings, no sign-offs
- Audience framing: "People with low literacy, limited education, and no English background — write as if speaking to a farmer or fisherman"
- Simple words / short sentences — one idea per sentence
- Phonetic spelling lists retained and tightened (TL/CEB)
- Section headings simplified to plain questions: "Where Is The Storm", "Who Is In Danger", "What To Do" (EN); "Nasaan ang Bagyo", "Ano ang Gagawin" (TL); "Asa ang Bagyo", "Unsa ang Buhaton" (CEB)

#### 3. ETL `_TTS_PROMPTS` — same audience framing + prohibitions applied

TTS prompts convert the radio Markdown script into plain text for synthesis. The EN prompt was weakest — no audience framing, no prohibition on placeholders.

**Fix across all three languages:**
- EN: rewritten with audience framing, no-placeholder rule, no-radio-show rule, simple words / short sentences
- TL/CEB: added explicit no-placeholder and no-radio-show rules on top of existing phonetic spelling requirements

#### 4. Notebook 08 TTS prompts synced to ETL

`notebooks/08-mms-tts-experiment.ipynb` cell `0f4d4183` now uses identical prompts to the ETL (audience framing, no placeholders, no radio show language, full phonetic spelling lists).

#### 5. Notebook 08 updated to reflect Coqui XTTS v2 as English TTS

Documented the full history of English TTS options tried:
- MMS English (`facebook/mms-tts-eng`) — ❌ robotic, rejected
- Microsoft SpeechT5 + HiFiGAN — ❌ scratchy, inconsistent voice, rejected
- Coqui XTTS v2 (`Damien Black`) — ✅ selected, matches production ETL

### Files changed

| File | Change |
|---|---|
| `modal_etl/step2_scripts.py` | `_RADIO_PROMPTS` rewritten; `_TTS_PROMPTS` updated with audience framing + prohibitions; `~750-word` docstring fixed |
| `notebooks/06-radio-bulletin.ipynb` | Word target 750 → 300, time references updated to 2 minutes |
| `notebooks/08-mms-tts-experiment.ipynb` | TTS prompts synced to ETL; English TTS history documented (MMS ❌, SpeechT5 ❌, XTTS v2 ✅) |

---

## PR #10 — Frontend UX Fixes: i18n, Storm Track, Read Bulletin
**Date:** 2026-04-19
**Branch:** `feature/frontend-ux-fixes`
**Status:** Complete ✅

### What we fixed

Three UX issues found while reviewing the live app, addressed in one PR.

---

#### 1. Full i18n — EN / TL / CEB

Every static label and bulletin text now switches language in real time when the visitor changes language.

**How it works:**
- `web/lib/translations.ts` — 19 translation keys across EN, Tagalog, Cebuano
- `web/components/LanguageProvider.tsx` — React context that reads `ws_language` from `localStorage` on mount and listens for `ws:language-change` events
- `web/components/PageLabel.tsx` — thin client component used inside server pages to translate a key without making the whole page a client component
- All three pages (`/`, `/storms/[id]`, `/bulletins/[id]`) and all relevant components wired up

**Language order / default changed:** Cebuano → Tagalog → English (was English-first). Default is now Cebuano.

#### 2. Storm Track Chart — fixed broken display

**Problem:** The "Storm Track" section rendered the full PAGASA bulletin PDF page (portrait, 1654×2339 A4) inside a forced landscape `aspect-[4/3]` container. With `object-contain`, the portrait image was letterboxed into a narrow rectangle surrounding by dark space — appearing empty or broken.

**Fix:** Replaced Next.js `<Image fill>` + fixed aspect ratio with a plain `<img className="w-full h-auto">` in both the storm and bulletin detail pages. The chart now renders at full width with its natural portrait proportions.

#### 3. Read Bulletin — Markdown rendering

**Problem:** The "Read bulletin" collapsible section displayed the raw Markdown radio script with `**`, `#`, `*` syntax as literal characters.

**Fix:** Installed `react-markdown` + `@tailwindcss/typography`. Script source is `script_path` (full Markdown radio script) — `tts_path` was considered but rejected because it contains phonetically spelled words (`ki-lo-me-tros`) that look odd on screen.

### Files changed

| File | Change |
|---|---|
| `web/lib/translations.ts` | New — 19 i18n keys × 3 languages |
| `web/components/LanguageProvider.tsx` | New — React context + `useTranslation` hook |
| `web/components/PageLabel.tsx` | New — thin client label for server pages |
| `web/app/layout.tsx` | Wrap body in `<LanguageProvider>` |
| `web/app/page.tsx` | Replace static strings with `<PageLabel>` |
| `web/app/storms/[stormId]/page.tsx` | `<PageLabel>` + chart display fix |
| `web/app/bulletins/[bulletinId]/page.tsx` | `<PageLabel>` + chart display fix |
| `web/components/AudioPlayer.tsx` | `useTranslation()` for labels |
| `web/components/AffectedAreas.tsx` | `useTranslation()` for labels |
| `web/components/LocationOnboarding.tsx` | `useTranslation()` for labels |
| `web/components/LanguageToggle.tsx` | CEB default, reorder to CEB→TL→EN |
| `web/components/BulletinAudioSection.tsx` | `useTranslation()` + `react-markdown` render |
| `web/lib/audio-url.ts` | Guard against missing `NEXT_PUBLIC_SUPABASE_URL` |
| `web/tailwind.config.ts` | Add `@tailwindcss/typography` plugin |
| `web/package.json` | Add `react-markdown`, `@tailwindcss/typography` |

---

## PR #12 — ETL Quality Fixes: Radio Script, Phonetics, Number Formatting, ETL Report
**Date:** 2026-04-19  
**Branch:** `main` (direct commits)  
**Commits:** `a1c4ce5`, `b7fc6af`, `a905c78`, `d5caf77`, `b41053e`

### What we fixed

#### 1. Radio script no longer shows phonetic spellings on screen

**Problem:** The "Read bulletin" section on the website displayed phonetically spelled words (`ki-lo-me-tros`, `tro-pi-kal`) because `_RADIO_PROMPTS` incorrectly included phonetic spelling lists — those belong only in `_TTS_PROMPTS`.

**Fix:** Removed all phonetic spelling lists from `_RADIO_PROMPTS` (CEB + TL). Replaced with natural language equivalents (e.g. `kph → kilometros sa usa ka oras`).

**Two-prompt rule clarified:**
- `_RADIO_PROMPTS` → `radio_{lang}.md` → displayed on screen — must use proper readable language
- `_TTS_PROMPTS` → `tts_{lang}.txt` → fed to audio synthesizer — uses phonetic spellings

#### 2. Numbers: digits in radio scripts, phonetic words in TTS

**Problem:** The LLM was instructed to spell out all numbers in Cebuano words, producing wrong output like `duha ka ka-lima` for 25.

**Fix:**
- `_RADIO_PROMPTS` (CEB + TL): now instructs to write numbers as digits + Cebuano/Tagalog unit words (e.g. `25 kilometros sa usa ka oras`)
- `_TTS_PROMPTS` (CEB + TL): added phonetic number tables using Spanish-borrowed words common in Filipino speech (baynte singko, isyento treynta, etc.)

#### 3. ETL run report

Added a local Markdown run report saved to `data/etl_reports/etl_report_{timestamp}.md` after each batch. Shows per-bulletin, per-step status, elapsed time, and files created. Useful for diagnosing failures without digging into Modal logs.

#### 4. Notebook 08 synced

TTS prompts in `notebooks/08-mms-tts-experiment.ipynb` synced to match ETL: number phonetics tables added for both CEB and TL.

### Files changed

| File | Change |
|---|---|
| `modal_etl/step2_scripts.py` | Remove phonetics from `_RADIO_PROMPTS`; digits rule + phonetic number tables in `_TTS_PROMPTS` |
| `modal_etl/run_batch.py` | Add `_write_report()`, timing + try/except per step, report saved to `data/etl_reports/` |
| `notebooks/08-mms-tts-experiment.ipynb` | Sync TTS prompts — phonetic number tables for CEB + TL |

---

## PR #13 — Parallelize Step 2 by Language
**Date:** 2026-04-20  
**Branch:** `feature/parallel-step2`  
**Commit:** `1bf626c`

### What we did

Step 2 (radio script + TTS text generation) previously ran all 3 languages sequentially in a single Modal container. Since Ollama handles one inference request at a time, EN → TL → CEB queued on the same GPU — ~4 minutes wall time.

Refactored Step 2 to match the pattern already used by Step 3: one Modal container per language, dispatched concurrently via `starmap`. Each container starts its own Ollama instance and processes a single language independently.

**Expected improvement:** ~4 min → ~1.5 min wall time for Step 2. GPU cost unchanged (same total GPU-minutes, distributed across 3 containers).

### Files changed

| File | Change |
|---|---|
| `modal_etl/step2_scripts.py` | `Step2Scripts` class → `step2_scripts` `@app.function(stem, language, force)` — timeout 3600s → 600s |
| `modal_etl/run_batch.py` | `scripts.run.remote()` → `step2_scripts.starmap(...)`, remove `Step2Scripts` instance, update ETL report label |

---
