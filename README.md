# WeatherSpeak PH

AI-powered multilingual severe weather communications for the Philippines.  
**Gemma 4 Good Hackathon — deadline May 18, 2026.**

---

## The Problem

PAGASA issues typhoon bulletins in English only. Most Filipinos most at risk — farmers, fisherfolk, rural communities — speak Tagalog or Cebuano (Bisaya), not English. When a typhoon is approaching, they may not understand the warning in time to act.

**But the language barrier is only half the problem.**

Even a Tagalog or Cebuano translation in text form leaves millions behind. According to the Philippine Statistics Authority's 2019 Functional Literacy, Education and Mass Media Survey (FLEMMS), roughly **8–9 million Filipinos aged 10–64 are functionally illiterate** — meaning they cannot read with sufficient comprehension to act on written instructions. In rural and coastal communities hardest hit by typhoons, that share is even higher.

A bulletin on a screen — in any language — cannot reach someone who cannot read it.

## What It Does

WeatherSpeak PH ingests PAGASA PDF bulletins, translates them into Tagalog and Cebuano, and generates MP3 audio so communities can *hear* the warning in their own language — on any phone, with no reading required.

> **Audio is the equaliser.** It crosses the language barrier *and* the literacy barrier in one step. A farmer in Leyte with a basic mobile phone and no schooling can press play and understand exactly what is coming and what to do.

---

## Architecture

### ETL Pipeline

Batch ETL runs on **Modal** (serverless GPU). Step 2 runs English first, then Tagalog and Cebuano in parallel (each translates from the English output). Step 3 synthesises all three languages in parallel.

```mermaid
flowchart LR
    PDF([PAGASA PDF\nBulletin])

    subgraph Step1["Step 1 — OCR & Extraction"]
        G1["🤖 Gemma 4 E4B\n(vision + OCR)\nor Marker PDF"]
        OCR["ocr.md · forecast_table.md\nchart.png · metadata.json"]
        G1 --> OCR
    end

    subgraph Step2["Step 2 — Script Generation"]
        EN["🤖 Gemma 4 E4B\nGenerates English script\n(≤400 words)"]
        TLCEB["🤖 Gemma 4 E4B × 2\nTranslates EN → Tagalog\nTranslates EN → Cebuano\n(parallel)"]
        TTS["TTS text pass\n(phonetic spellings)"]
        EN --> TLCEB --> TTS
    end

    subgraph Step3["Step 3 — Speech Synthesis  ‹parallel × 3›"]
        TTS1["Facebook MMS VITS\n(Tagalog + Cebuano)"]
        TTS2["Coqui XTTS v2\n(English)"]
        MP3["audio_en.mp3\naudio_tl.mp3\naudio_ceb.mp3"]
        TTS1 --> MP3
        TTS2 --> MP3
    end

    subgraph Step4["Step 4 — Publish"]
        SB["Supabase Storage\n+ PostgreSQL"]
    end

    PDF --> Step1 --> Step2 --> Step3 --> Step4
```

### End-to-End Flow

Shows the full journey from PAGASA publishing a bulletin to a community member hearing it in their language, and where Gemma 4 is used.

```mermaid
flowchart TD
    PAGASA(["🌀 PAGASA publishes\ntyphoon bulletin PDF"])

    subgraph ETL["Modal ETL  —  serverless GPU batch job"]
        direction TB
        OCR["Step 1\n🤖 Gemma 4 E4B reads the PDF\nTwo-pass: narrative fields + forecast table\nExtracts storm track chart · outputs structured metadata\n(Marker PDF backend available as alternative)"]
        SCRIPTS["Step 2  ‹EN first, then TL + CEB in parallel›\n🤖 Gemma 4 E4B\n1. Generate English radio script (≤400 words) from OCR + metadata\n2. Translate English → Tagalog · English → Cebuano\n3. TTS text pass: phonetic spellings + number/time conversion"]
        TTS["Step 3  ‹EN · TL · CEB in parallel›\nMMS VITS synthesises Tagalog + Cebuano audio\nXTTS v2 synthesises English audio"]
        UPLOAD["Step 4\nUploads MP3s + scripts + chart\nto Supabase Storage + PostgreSQL"]
        OCR --> SCRIPTS --> TTS --> UPLOAD
    end

    subgraph WEB["Next.js PWA  —  Vercel"]
        direction TB
        SITE["weatherspeak-ph.vercel.app"]
        PLAYER["Audio player with waveform\n(EN · TL · CEB)"]
        SCRIPT["Read bulletin\n(Markdown radio script)"]
        PDF_PREV["PDF preview\n(original PAGASA bulletin)"]
        GEO["Distance to storm\n(geolocation)"]
        SITE --> PLAYER
        SITE --> SCRIPT
        SITE --> PDF_PREV
        SITE --> GEO
    end

    USER(["👨‍🌾 Filipino farmer /\nfisherfolk / community member\nhears warning in their language"])

    PAGASA --> ETL --> WEB --> USER

    style OCR fill:#fef3c7,stroke:#d97706,color:#000
    style SCRIPTS fill:#fef3c7,stroke:#d97706,color:#000
    style PAGASA fill:#fee2e2,stroke:#dc2626,color:#000
    style USER fill:#dcfce7,stroke:#16a34a,color:#000
```

> 🤖 **Gemma 4 E4B** is used in Steps 1 and 2. In Step 1 it reads the raw PDF pages with vision, extracts all narrative bulletin fields, and describes the storm track chart. In Step 2 it generates a plain English radio script from the extracted data, then translates that script into Tagalog and Cebuano — ensuring both translations are grounded in the same verified English text.

---

## Stack

| Layer | Technology |
|---|---|
| OCR backend (default) | Marker PDF (Surya layout-aware extractor) + Gemma 4 chart description |
| OCR backend (alternative) | Gemma 4 E4B vision via Ollama (`gemma4:e4b`) — `--backend gemma4` |
| Script generation | Gemma 4 E4B via Ollama (`gemma4:e4b`) |
| TTS — Cebuano / Tagalog | Facebook MMS VITS (`facebook/mms-tts-ceb`, `facebook/mms-tts-tgl`) |
| TTS — English | Coqui XTTS v2 (`tts_models/multilingual/multi-dataset/xtts_v2`) |
| GPU compute | Modal (serverless A10G) |
| Frontend | Next.js 14 / Vercel (PWA, mobile-first, CEB/TL/EN i18n) |
| Storage | Supabase Storage + PostgreSQL |
| Package manager | uv |
| Python | 3.12+ |

---

## Languages

| Language | Code | TTS model |
|---|---|---|
| English | `en` | Coqui XTTS v2 (Damien Black voice) |
| Tagalog | `tl` | Facebook MMS VITS (`mms-tts-tgl`) |
| Cebuano | `ceb` | Facebook MMS VITS (`mms-tts-ceb`) |

---

## Running the ETL

```bash
# First time — initialise Modal volumes:
uv run modal run modal_etl/setup_volumes.py::setup_ollama_volume
uv run modal run modal_etl/setup_volumes.py::setup_tts_volume

# Process the 3 most recent bulletins (Marker PDF backend is the default):
uv run modal run modal_etl/run_batch.py --n 3

# Use Gemma 4 vision for OCR instead (slower but no external dependency):
uv run modal run modal_etl/run_batch.py --n 3 --backend gemma4

# Force re-run all steps even if outputs exist:
uv run modal run modal_etl/run_batch.py --n 1 --force

# Re-run a specific bulletin by stem (useful for fixing one bulletin):
uv run modal run modal_etl/run_batch.py --stem "PAGASA_25-TC22_Verbena_TCB#24" --force

# Use --detach when processing many bulletins — submits the job to Modal and
# returns immediately so your local terminal doesn't time out waiting for logs.
uv run modal run --detach modal_etl/run_batch.py --n 5

# Force re-run across multiple bulletins without risking a local timeout:
uv run modal run --detach modal_etl/run_batch.py --n 5 --force
```

ETL run reports are saved to `data/etl_reports/etl_report_{timestamp}.md`.

---

## Project Structure

```
modal_etl/                    # ETL pipeline (Modal functions)
  run_batch.py                # Batch entrypoint — orchestrates all 4 steps
  step1_ocr.py                # Thin Modal wrapper → core/ocr.py or core/ocr_marker.py
  step2_scripts.py            # Thin Modal wrapper → core/scripts.py
  step3_tts.py                # Thin Modal wrapper → core/tts.py
  step4_upload.py             # Supabase upload + DB upsert
  phonetics.py                # Deterministic phonetic post-processing for TL/CEB TTS
  core/                       # Business logic — importable locally (no Modal needed)
    ocr.py                    # Two-pass OCR: narrative extraction + forecast table
    ocr_marker.py             # Marker PDF backend + Gemma 4 chart description
    ollama.py                 # Shared Ollama HTTP helpers
    scripts.py                # EN-first script generation + TL/CEB translation
    tts.py                    # MMS VITS + Coqui XTTS v2 synthesis
  synthesizers/               # Low-level TTS synthesizer classes
    mms.py                    # Facebook MMS VITS
    xtts.py                   # Coqui XTTS v2

web/                          # Next.js 14 PWA frontend
  app/                        # App Router pages (Home · Storm · Bulletin)
  components/                 # React components (AudioPlayer, BulletinHistory, …)
  lib/                        # Supabase queries, i18n translations, geography utils

notebooks/                    # Numbered Jupyter notebooks — primary dev/research artifacts
  01-ocr-setup-and-data.ipynb
      # Project setup: installs dependencies, clones the pagasa-parser/bulletin-archive
      # repo, and selects two representative bulletins (Pepito SWB#01, Basyang TCA#01)
      # as the baseline test set used throughout all experiments.

  02-surya-ocr.ipynb
      # Evaluates Surya OCR (AI-native, 90+ languages) on PAGASA bulletin PDFs.
      # Tests layout detection, reading-order reconstruction, and raw text extraction
      # quality. Establishes the first accuracy baseline for the OCR comparison.

  03-marker.ipynb
      # Evaluates Marker PDF — a document conversion toolkit built on Surya that
      # outputs clean Markdown with preserved tables and extracted figures.
      # Key finding: Marker handles the multi-column bulletin layout and forecast
      # table far better than raw Surya, and saves chart images alongside the text.

  04-gemma4.ipynb
      # Tests the vision-first hypothesis: can Gemma 4 E4B replace a dedicated OCR
      # engine? Sends each bulletin page as a base64 image to Ollama and prompts
      # Gemma to extract all bulletin fields plus a structured JSON summary.
      # Validates the two-pass approach (narrative fields + forecast table separately).

  05-comparison.ipynb
      # Side-by-side comparison of Surya, Marker, and Gemma 4 E4B on speed,
      # field-extraction accuracy, and table fidelity. Outcome: Marker is selected
      # as the default OCR backend (best text + table quality); Gemma 4 E4B is
      # retained for storm track chart description where vision is required.

  06-radio-bulletin.ipynb
      # First radio script generator: prompts Gemma 4 E4B to convert raw OCR markdown
      # into a ~200-word spoken bulletin in English, Tagalog, and Cebuano.
      # Experiments with prompt style, word count, tone, and field ordering to produce
      # natural, radio-ready prose for each language.

  07-tts-experiment.ipynb
      # Text-to-speech experiments with Coqui XTTS v2. Converts the English radio
      # scripts to MP3 using the "Damien Black" voice clone. Explores chunking
      # strategy (sentence-boundary splits ≤200 chars) and language-code mapping
      # (Tagalog/Cebuano → Spanish phonemes as the closest available approximation).

  08-mms-tts-experiment.ipynb
      # Introduces Facebook MMS VITS as the TTS engine for Tagalog and Cebuano —
      # native models that eliminate the Spanish-phoneme approximation. Compares
      # MMS output quality against XTTS v2. Also refines the radio script pipeline:
      # switches from raw OCR to structured metadata JSON as the LLM input to fix
      # hallucinations (e.g. wind speed confused with movement speed).

  09-pipeline-validation.ipynb
      # Validates the full OCR → structured metadata → radio scripts → TTS text
      # chain across multiple bulletins. Checks JSON schema conformance for metadata,
      # script word counts, and TTS text cleanup. Serves as a pre-production smoke
      # test before the Modal ETL is built.

  10-etl-e2e.ipynb
      # Full end-to-end ETL run using modal_etl/core/ modules locally — no Modal
      # required. Runs Steps 1–3 (OCR, scripts, TTS) against a real bulletin PDF
      # and writes output to notebooks/10-etl-e2e/output/{stem}/. Used for
      # iterative prompt development and regression testing before deploying to Modal.

data/
  bulletin-archive/           # Source PAGASA PDFs (gitignored)
  etl_reports/                # ETL run reports — etl_report_{timestamp}.md (gitignored)
  radio_bulletins/            # Generated scripts and TTS text (local cache, gitignored)

tests/                        # Python test suite (191 tests)
docs/superpowers/             # Design specs and implementation plans
```

---

## Hackathon Tracks

- **Impact — Digital Equity & Inclusivity**
- **Impact — Global Resilience**
- **Special Technology — Ollama**
- **Main Track**

---

## Development Log

See [`devlog.md`](devlog.md) for a full record of progress by PR.
