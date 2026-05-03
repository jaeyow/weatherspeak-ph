# Notebooks — WeatherSpeak PH

Research and development notebooks for the WeatherSpeak PH ETL pipeline.
Each notebook builds on the previous one, progressing from raw OCR experiments
to a fully working end-to-end pipeline.

---

## Experiment Progression

### 01. [OCR Setup and Data Collection](01-ocr-setup-and-data.ipynb)

**Goal:** Environment setup and test data preparation.

- Clones the `pagasa-parser/bulletin-archive` GitHub repo
- Selects two representative bulletins as the baseline test set used in all experiments:
  - `PAGASA_20-19W_Pepito_SWB#01` — Severe Weather Bulletin
  - `PAGASA_22-TC02_Basyang_TCA#01` — Tropical Cyclone Alert
- Converts PDFs to images (200 DPI) for OCR ingestion
- Installs and verifies core dependencies

---

### 02. [Surya OCR Testing](02-surya-ocr.ipynb)

**Goal:** Evaluate Surya OCR as the first OCR candidate.

- Surya is an AI-native OCR toolkit (90+ languages, beats Google Cloud Vision on benchmarks)
- Tests layout detection, reading-order reconstruction, and raw text extraction quality on PAGASA bulletins
- Establishes the first accuracy baseline for the three-way OCR comparison

---

### 03. [Marker PDF Testing](03-marker.ipynb)

**Goal:** Evaluate Marker as a document conversion alternative to Surya.

- Marker is built on top of Surya and outputs clean Markdown with preserved tables and extracted figures
- Handles the multi-column PAGASA bulletin layout and storm forecast table far better than raw Surya
- Saves storm track chart images alongside the extracted text — a requirement for Step 2 chart description
- Key finding: Marker's structured Markdown output is a much better LLM input than raw OCR text

---

### 04. [Gemma 4 Vision Testing](04-gemma4.ipynb)

**Goal:** Test the vision-first hypothesis — can Gemma 4 replace a dedicated OCR engine?

- Sends each bulletin page as a base64 image to Gemma 4 E4B via Ollama
- Two-pass approach: first pass extracts all narrative bulletin fields; second pass extracts the forecast table
- Generates structured JSON output validated against a schema
- Finding: Gemma 4 vision accuracy is sufficient for bulletins, but slower than Marker and loses table structure

---

### 05. [OCR Comparison Analysis](05-comparison.ipynb) ✅ Decision

**Goal:** Side-by-side comparison of all three OCR approaches to select the production backend.

- Compares Surya, Marker, and Gemma 4 E4B on processing speed, field-extraction accuracy, and table fidelity
- **Outcome — Hybrid pipeline selected:**
  - **Marker PDF** is the default OCR backend (best text + table quality, structured Markdown output)
  - **Gemma 4 E4B** is retained for storm track chart description (only a vision model can interpret the map)
  - Pure Gemma 4 vision (Scenario A) was not selected — Marker is faster and more reliable for text extraction

---

### 06. [Radio Bulletin Generator](06-radio-bulletin.ipynb)

**Goal:** First end-to-end radio script generator using Gemma 4 E4B.

- Prompts Gemma 4 E4B to convert OCR markdown into a ~200-word spoken bulletin
- Generates scripts in English, Tagalog, and Cebuano
- Experiments with prompt style, tone, word count, and field ordering
- Output: flowing prose suitable for radio broadcast — no bullet points, no markdown

---

### 07. [TTS Experiment — Coqui XTTS v2](07-tts-experiment.ipynb)

**Goal:** Convert English radio scripts to MP3 using Coqui XTTS v2.

- Uses the "Damien Black" voice clone for English synthesis
- Develops the sentence-boundary chunking strategy (≤200 chars per XTTS v2 call)
- Language-code mapping: Tagalog and Cebuano mapped to Spanish phonemes as the closest available approximation
- Finding: XTTS v2 produces good English audio but the Spanish-phoneme workaround is imperfect for TL/CEB

---

### 08. [TTS Experiment — Facebook MMS VITS](08-mms-tts-experiment.ipynb)

**Goal:** Evaluate Facebook MMS VITS as a native TTS replacement for Tagalog and Cebuano.

- MMS provides dedicated `mms-tts-tgl` (Tagalog) and `mms-tts-ceb` (Cebuano) models — no phoneme approximation needed
- Compares MMS output quality against XTTS v2 for TL/CEB; MMS wins on naturalness
- Also fixes a hallucination bug: switches from raw `ocr.md` to structured `metadata.json` as the LLM input
  (raw OCR caused Gemma to confuse wind speed with movement speed — no field labels in unstructured text)
- **Outcome:** MMS VITS selected for Tagalog + Cebuano; XTTS v2 retained for English

---

### 09. [Pipeline Validation](09-pipeline-validation.ipynb)

**Goal:** Validate the full OCR → metadata → scripts → TTS chain before building the Modal ETL.

- Checks JSON schema conformance for extracted metadata across multiple bulletins
- Validates radio script word counts and language correctness
- Validates TTS text cleanup (digit conversion, English word removal for TL/CEB)
- Serves as a pre-production smoke test — confirms the pipeline is stable enough to deploy

---

### 10. [End-to-End ETL (Local)](10-etl-e2e.ipynb)

**Goal:** Run the full production pipeline locally using `modal_etl/core/` modules — no Modal required.

- Imports `run_step1`, `run_step2`, `run_step3` directly from the production codebase
- Runs Steps 1–3 (OCR, scripts, TTS) against a real bulletin PDF
- Output mirrors the Modal Volume layout: `output/{stem}/ocr.md`, `radio_{lang}.md`, `audio_{lang}.mp3`
- Used for iterative prompt development and regression testing before deploying changes to Modal

---

## Quick Start

```bash
# Install dependencies (use uv, not pip)
uv pip install marker-pdf transformers torch

# Start Ollama (required for Steps 1 and 2)
ollama pull gemma4:e4b
ollama serve

# Run notebooks in order (01 → 10)
jupyter notebook
```

---

## Output Structure

```
data/
├── bulletin-archive/       # Source PAGASA PDFs
├── surya_results/          # Surya OCR outputs
├── marker_results/         # Marker outputs (markdown + extracted chart images)
├── gemma4_results/         # Gemma 4 vision outputs + structured JSON
├── radio_bulletins/        # Radio scripts: *_radio_{en,tl,ceb}.md
└── tts_output/             # MP3 files: *_audio_{en,tl,ceb}.mp3

notebooks/10-etl-e2e/output/{stem}/
├── ocr.md                  # Marker OCR output
├── metadata.json           # Structured storm metadata
├── chart.png               # Storm track chart (extracted by Marker)
├── radio_{en,tl,ceb}.md    # Radio scripts
├── tts_{en,tl,ceb}.txt     # TTS-ready plain text
└── audio_{en,tl,ceb}.mp3   # Synthesised audio
```

---

## Related

- [`modal_etl/`](../modal_etl/) — Production ETL (mirrors the notebook pipeline, runs on Modal GPU)
- [`devlog.md`](../devlog.md) — Development progress log
- [`README.md`](../README.md) — Project overview
