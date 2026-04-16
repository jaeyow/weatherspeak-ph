# Modal ETL Pipeline Design

**Date:** 2026-04-16
**Author:** Jose Reyes

---

## Problem

The WeatherSpeak PH pipeline (PDF → OCR → radio scripts → MP3) has been validated end-to-end in Jupyter notebooks. It now needs to run on Modal so bulletins can be batch-converted offline and the resulting MP3s served to the future website.

---

## Goals

1. Run the full 3-step pipeline on Modal using serverless GPU (steps 1-2) and CPU (step 3)
2. Store all generated artifacts in a Modal Volume accessible by the future website
3. Process the newest N severe weather events (latest bulletin per event) from the `pagasa-parser/bulletin-archive` GitHub repo
4. Keep TTS model implementations behind a clean interface so they can be swapped later without touching pipeline logic

---

## Scope

- Offline batch conversion only — no real-time triggering, no PAGASA polling
- Bulletin selection: newest N severe weather events, latest bulletin (`#NN`) per event
- Languages: English (EN), Tagalog (TL), Cebuano (CEB)
- TTS: MMS VITS for CEB/TL, SpeechT5 for EN
- Storage: Modal Volumes (no Supabase in this phase)

---

## Pipeline

```
pagasa-parser/bulletin-archive (GitHub)
  ↓  bulletin_selector.py — list → group by event → newest N → latest bulletin each

[Local] run_batch.py  ←  @app.local_entrypoint
  │
  ├─► step1_ocr.remote(pdf_url)          GPU container (A10G)
  │     Ollama + gemma4:e4b
  │     PDF → ocr.md → saved to Volume
  │     returns: stem
  │
  ├─► step2_scripts.remote(stem)         GPU container (A10G)
  │     Ollama + gemma4:e4b
  │     ocr.md → radio_{lang}.md × 3 + tts_{lang}.txt × 3 → saved to Volume
  │     returns: stem
  │
  └─► step3_tts.starmap([               CPU containers × 3 (parallel per language)
        (stem, "ceb"),                   MMSSynthesizer → audio_ceb.mp3
        (stem, "tl"),                    MMSSynthesizer → audio_tl.mp3
        (stem, "en"),                    SpeechT5Synthesizer → audio_en.mp3
      ])
```

**Bulletin stem** — the PDF filename without the `.pdf` extension (e.g. `PAGASA_22-TC02_Basyang_TCA#01`). Used as the primary key for all artifacts throughout the pipeline.

---

## File Layout

```
modal_etl/
  app.py                  # Modal app, Image & Volume definitions
  config.py               # N (events to process), language list, GPU spec, Volume mount paths
  run_batch.py            # @app.local_entrypoint — orchestration
  bulletin_selector.py    # GitHub API: list PDFs → group by event → newest N → latest bulletin each
  step1_ocr.py            # @app.function (GPU) — Gemma 4 E4B OCR → ocr.md
  step2_scripts.py        # @app.function (GPU) — Gemma 4 E4B → radio .md + TTS .txt per language
  step3_tts.py            # @app.function (CPU) — TTSSynthesizer → MP3 per language
  synthesizers/
    base.py               # TTSSynthesizer Protocol
    mms.py                # MMSSynthesizer — wraps facebook/mms-tts-ceb and mms-tts-tgl
    speecht5.py           # SpeechT5Synthesizer — wraps microsoft/speecht5_tts
```

Logic for each step is extracted and adapted directly from notebooks 04, 06, and 08. No net-new inference logic.

---

## Output Volume Structure

All artifacts stored under `/output/{stem}/` in the `weatherspeak-output` Volume:

```
/output/PAGASA_22-TC02_Basyang_TCA#01/
  ocr.md
  radio_en.md
  radio_tl.md
  radio_ceb.md
  tts_en.txt
  tts_tl.txt
  tts_ceb.txt
  audio_en.mp3
  audio_tl.mp3
  audio_ceb.mp3
```

---

## Modal Infrastructure

### Volumes

| Volume | Contents |
|---|---|
| `weatherspeak-ollama` | Gemma 4 E4B model weights (pulled once, reused across runs) |
| `weatherspeak-tts-models` | MMS and SpeechT5 HuggingFace weights (downloaded once, reused) |
| `weatherspeak-output` | All generated artifacts (ocr.md, radio .md, tts .txt, .mp3) |

### Container Images

**`ollama_image`** (steps 1 & 2):
- Ubuntu base + Ollama CLI
- `gemma4:e4b` weights stored in `weatherspeak-ollama` Volume (not baked into image)
- Ollama server started via `@modal.enter()` subprocess at container startup
- `OLLAMA_MODELS` env var points to Volume mount path

**`tts_image`** (step 3):
- Python + `transformers`, `torch`, `pydub`
- MMS and SpeechT5 weights cached in `weatherspeak-tts-models` Volume

### GPU

Steps 1 and 2: `modal.gpu.A10G()` — sufficient for Gemma 4 E4B (4B parameters).
Step 3: CPU-only.

### Cold Starts

No `keep_warm` — this is an offline batch job. Each batch run incurs one cold start (~30-60s for Ollama server startup + model load from Volume) then processes all bulletins without interruption. Acceptable for occasional batch conversion.

---

## TTS Abstraction

`step3_tts.py` routes synthesis through a `TTSSynthesizer` protocol, never calling model APIs directly. This allows any synthesizer to be swapped by writing a new class and updating one line in `config.py`.

### Protocol (`synthesizers/base.py`)

```python
class TTSSynthesizer(Protocol):
    def load(self) -> None: ...
    def synthesize(
        self,
        sentences: list[tuple[str, bool]],
        output_path: Path,
    ) -> Path: ...
```

`sentences` is a list of `(text, is_paragraph_end)` tuples — same format produced by `prepare_mms_sentences()` and `prepare_english_sentences()` from notebook 08.

### Concrete Implementations

| Class | File | Model |
|---|---|---|
| `MMSSynthesizer` | `synthesizers/mms.py` | `facebook/mms-tts-ceb`, `facebook/mms-tts-tgl` |
| `SpeechT5Synthesizer` | `synthesizers/speecht5.py` | `microsoft/speecht5_tts` + `speecht5_hifigan` |

### Language Routing (`config.py`)

```python
SYNTHESIZER_MAP = {
    "ceb": MMSSynthesizer("facebook/mms-tts-ceb"),
    "tl":  MMSSynthesizer("facebook/mms-tts-tgl"),
    "en":  SpeechT5Synthesizer("microsoft/speecht5_tts"),
}
```

To replace a model: implement a new class satisfying `TTSSynthesizer`, update the relevant entry in `SYNTHESIZER_MAP`. No other files change.

---

## Bulletin Selection (`bulletin_selector.py`)

1. Fetch file listing from `pagasa-parser/bulletin-archive` via GitHub API
2. Filter to PDF files only
3. Parse storm event identifier from filename (e.g. `Pepito`, `Basyang`)
4. Group bulletins by event identifier (storm name extracted from filename)
5. Within each group, sort by bulletin sequence number (the `#NN` suffix) descending — take the highest number as the latest bulletin
6. Sort events by the bulletin number of their latest bulletin descending — higher numbers indicate more recent events; take newest N
6. Return list of `(stem, raw_github_pdf_url)` pairs

`N` is set in `config.py`. Default: `10`.

---

## Orchestration (`run_batch.py`)

```python
@app.local_entrypoint()
def main():
    bulletins = get_latest_bulletins(N)           # bulletin_selector
    for pdf_url, stem in bulletins:
        stem = step1_ocr.remote(pdf_url)
        stem = step2_scripts.remote(stem)
        list(step3_tts.starmap(
            [(stem, lang) for lang in ["ceb", "tl", "en"]]
        ))
```

Bulletins are processed sequentially (one at a time) to keep GPU costs predictable. The three language TTS jobs within each bulletin run in parallel via `.starmap()`.

---

## Error Handling

- If a step fails for a bulletin, that bulletin is skipped and the error is logged. Remaining bulletins continue.
- Each step checks for existing output in the Volume before running — if artifacts already exist for a stem, the step is skipped. This makes the batch re-runnable without re-processing completed bulletins.
- Model weights are validated at container startup; missing weights raise immediately with a clear message.

---

## Out of Scope

- Real-time PAGASA bulletin polling or webhook triggering
- Supabase storage integration (follow-on work for the website phase)
- Frontend/website (separate project)
- Processing all bulletins for a storm event (latest only, per design decision)
- TL and EN dialect-pure TTS text generation improvements (notebook 08 follow-on)
- Fine-tuning or retraining any model
