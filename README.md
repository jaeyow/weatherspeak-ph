# WeatherSpeak PH

AI-powered multilingual severe weather communications for the Philippines.  
**Gemma 4 Good Hackathon — deadline May 18, 2026.**

---

## The Problem

PAGASA issues typhoon bulletins in English only. Most Filipinos most at risk — farmers, fisherfolk, rural communities — speak Tagalog or Cebuano (Bisaya), not English. When a typhoon is approaching, they may not understand the warning in time to act.

## What It Does

WeatherSpeak PH ingests PAGASA PDF bulletins, translates them into Tagalog and Cebuano, and generates MP3 audio so communities can *hear* the warning in their own language — on any phone, with no reading required.

---

## Architecture

### ETL Pipeline

Batch ETL runs on **Modal** (serverless GPU). Steps 2 and 3 each spin up one container per language and run all three concurrently.

```mermaid
flowchart LR
    PDF([PAGASA PDF\nBulletin])

    subgraph Step1["Step 1 — OCR & Extraction"]
        G1["🤖 Gemma 4 E4B\n(vision + OCR)"]
        OCR["ocr.md\nchart.png\nmetadata.json"]
        G1 --> OCR
    end

    subgraph Step2["Step 2 — Script Generation  ‹parallel × 3 languages›"]
        G2["🤖 Gemma 4 E4B\n(translation + phonetics)"]
        S2OUT["radio_en.md · radio_tl.md · radio_ceb.md\ntts_en.txt · tts_tl.txt · tts_ceb.txt"]
        G2 --> S2OUT
    end

    subgraph Step3["Step 3 — Speech Synthesis  ‹parallel × 3 languages›"]
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
        OCR["Step 1\n🤖 Gemma 4 E4B reads the PDF\nExtracts bulletin text + storm track chart\nOutputs structured metadata"]
        SCRIPTS["Step 2  ‹EN · TL · CEB in parallel›\n🤖 Gemma 4 E4B translates + adapts\nWrites 300-word radio scripts\nPhonetically spells words for TTS"]
        TTS["Step 3  ‹EN · TL · CEB in parallel›\nMMS VITS synthesises Tagalog + Cebuano audio\nXTTS v2 synthesises English audio"]
        UPLOAD["Step 4\nUploads MP3s + scripts + chart\nto Supabase Storage + PostgreSQL"]
        OCR --> SCRIPTS --> TTS --> UPLOAD
    end

    subgraph WEB["Next.js PWA  —  Vercel"]
        direction TB
        SITE["weatherspeak-ph.vercel.app"]
        PLAYER["Audio player\n(EN · TL · CEB)"]
        SCRIPT["Read bulletin\n(Markdown radio script)"]
        SITE --> PLAYER
        SITE --> SCRIPT
    end

    USER(["👨‍🌾 Filipino farmer /\nfisherfolk / community member\nhears warning in their language"])

    PAGASA --> ETL --> WEB --> USER

    style OCR fill:#fef3c7,stroke:#d97706,color:#000
    style SCRIPTS fill:#fef3c7,stroke:#d97706,color:#000
    style PAGASA fill:#fee2e2,stroke:#dc2626,color:#000
    style USER fill:#dcfce7,stroke:#16a34a,color:#000
```

> 🤖 **Gemma 4 E4B** is used in Steps 1 and 2 — it reads the raw English PDF, understands the storm track chart, and produces natural-sounding Tagalog and Cebuano radio scripts with correct phonetic spellings for the TTS synthesisers.

---

## Stack

| Layer | Technology |
|---|---|
| OCR + translation | Gemma 4 E4B via Ollama (`gemma4:e4b`) |
| TTS — Cebuano / Tagalog | Facebook MMS VITS (`facebook/mms-tts-ceb`, `facebook/mms-tts-tgl`) |
| TTS — English | Coqui XTTS v2 (`tts_models/multilingual/multi-dataset/xtts_v2`) |
| GPU compute | Modal (serverless A10G) |
| Frontend | Next.js / Vercel (PWA, mobile-first, CEB/TL/EN i18n) |
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

# Process the 3 most recent bulletins:
uv run modal run modal_etl/run_batch.py --n 3

# Force re-run all steps even if outputs exist:
uv run modal run modal_etl/run_batch.py --n 1 --force

# Use --detach when processing many bulletins — submits the job to Modal and
# returns immediately so your local terminal doesn't time out waiting for logs.
# The ETL continues running on Modal's infrastructure in the background.
uv run modal run --detach modal_etl/run_batch.py --n 5

# Force re-run all steps across multiple bulletins without risking a local timeout:
uv run modal run --detach modal_etl/run_batch.py --n 5 --force
```

ETL run reports are saved to `data/etl_reports/etl_report_{timestamp}.md`.

---

## Project Structure

```
modal_etl/           # ETL pipeline (Modal functions)
  run_batch.py       # Batch entrypoint — orchestrates all 4 steps
  step1_ocr.py       # Gemma 4 OCR + chart extraction
  step2_scripts.py   # Radio script + TTS text generation (3 languages in parallel)
  step3_tts.py       # Speech synthesis (3 languages in parallel)
  step4_upload.py    # Supabase upload + DB upsert
  phonetics.py       # Deterministic phonetic post-processing for TL/CEB TTS
  synthesizers/      # MMSSynthesizer, CoquiXTTSSynthesizer

web/                 # Next.js PWA frontend
  app/               # App Router pages
  components/        # React components
  lib/               # Shared utilities + i18n

notebooks/           # Numbered Jupyter notebooks — primary dev artifacts
  04-gemma4.ipynb    # OCR + structured JSON extraction
  06-radio-bulletin.ipynb  # Radio script generation
  08-mms-tts-experiment.ipynb  # TTS synthesis experiments

data/
  radio_bulletins/   # Generated scripts and TTS text files (local cache)
  etl_reports/       # ETL run reports (generated at runtime, gitignored)

tests/               # Python test suite
docs/superpowers/    # Design specs and implementation plans
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
