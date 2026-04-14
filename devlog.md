# WeatherSpeak PH — Development Log

Ongoing record of progress made during the Gemma 4 Good Hackathon (deadline: May 18, 2026).
Each entry corresponds to a pull request or significant milestone.

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
