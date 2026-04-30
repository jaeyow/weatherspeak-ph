# WeatherSpeak PH — Claude Code Context

AI-powered multilingual severe weather communications for the Philippines.
Gemma 4 Good Hackathon — deadline **May 18, 2026**.

---

## Project Goal

PAGASA issues typhoon bulletins in English only. WeatherSpeak PH translates them into
Tagalog and Cebuano (Bisaya) and generates audio MP3s so Filipino communities can hear
warnings in their own language.

**Hackathon tracks:** Impact (Digital Equity), Impact (Global Resilience), Ollama Special Track, Main Track.

---

## ETL Pipeline (4 steps)

```
PAGASA PDF
  → Step 1 [nb 10]: Marker PDF (default) or Gemma 4 E4B vision — OCR + storm chart → ocr.md + metadata.json
  → Step 2 [nb 10]: Gemma 4 E4B — EN script first, then TL + CEB translate from EN → radio_{lang}.md
  → Step 3 [nb 10]: Facebook MMS VITS (TL/CEB) + Coqui XTTS v2 (EN) — TTS → audio_{lang}.mp3
  → Step 4:         Upload MP3s + scripts + metadata to Supabase Storage + PostgreSQL
```

Batch ETL on Modal (not real-time). Default OCR backend is Marker PDF (`--backend marker`); use `--backend gemma4` for Gemma 4 vision.

---

## Stack

| Layer | Technology |
|---|---|
| OCR + translation | Gemma 4 E4B via Ollama (`gemma4:e4b`) |
| TTS | Coqui XTTS v2 (`tts_models/multilingual/multi-dataset/xtts_v2`) |
| Production GPU | Modal (serverless) |
| Frontend | Next.js / Vercel (PWA, mobile-first) — not started yet |
| Storage | Supabase / PostgreSQL — not started yet |
| Package manager | **uv** (never pip) |
| Python | 3.12+ |

---

## Model Decisions

- **Gemma 4 E4B** is the current working model — fast enough locally via Ollama.
- **Gemma 4 26B** is a future experiment: test quantized (4-bit/8-bit) to see if it runs
  fast enough on local hardware to be worth using in production. Do not switch until tested.
- **Ollama API** runs at `http://localhost:11434`. Always verify it's running before inference.

---

## Language Handling

| Language | Code | XTTS v2 phoneme |
|---|---|---|
| English | `en` | `en` |
| Tagalog | `tl` | `es` (Spanish — best phoneme approximation) |
| Cebuano | `ceb` | `es` (same rationale as Tagalog) |

No Cebuano TTS exists in XTTS v2 — Spanish phonemes are used as an acceptable Phase 1
fallback. A community Coqui Tagalog model (`tts_models/tl/...`) is a future alternative.

---

## Directory Structure

```
notebooks/          # Numbered sequentially — primary dev artifacts
  01-ocr-setup-and-data.ipynb
  02-surya-ocr.ipynb
  03-marker.ipynb
  04-gemma4.ipynb         # OCR + structured JSON extraction
  05-comparison.ipynb     # Decision: Scenario A (vision-first) selected
  06-radio-bulletin.ipynb # Radio scripts: EN / TL / CEB
  07-tts-experiment.ipynb # TTS → MP3 (in progress)

data/
  gemma4_results/         # Markdown + structured JSON from nb 04
  radio_bulletins/        # Radio scripts from nb 06 (*.md)
  tts_output/             # MP3 files from nb 07 (*.mp3)

docs/superpowers/
  specs/                  # Design specs (brainstorming output)
  plans/                  # Implementation plans

tests/                    # Standalone Python test files (not notebook cells)
```

---

## Sample Bulletins

Two bulletins are used throughout all experiments:

| Stem | Type | Storm |
|---|---|---|
| `PAGASA_20-19W_Pepito_SWB#01` | Severe Weather Bulletin | Tropical Depression Pepito |
| `PAGASA_22-TC02_Basyang_TCA#01` | Tropical Cyclone Alert | Basyang |

File naming convention: `{stem}_radio_{lang}.md` / `{stem}_radio_{lang}.mp3`

---

## Conventions

- **Always use `uv`** — `uv pip install`, `uv run python`, never bare `pip` or `python`
- **Notebooks are the primary artifact** — keep cells clean and runnable top-to-bottom
- **Commit after each logical unit** — don't batch unrelated changes
- **No fine-tuning** — using Gemma 4 off-the-shelf, no Unsloth or LoRA in scope
- **Server-side inference only** — no offline/edge deployment planned

---

## Workflow

This project uses Superpowers skills for planning and execution:
- New features: brainstorm → spec (`docs/superpowers/specs/`) → plan (`docs/superpowers/plans/`)
- Plans are executed via `superpowers:subagent-driven-development`
- Devlog is maintained in `devlog.md` — update after each PR

---

## ETL Operations

### Normal batch run (pick up latest bulletins)
```bash
uv run modal run modal_etl/run_batch.py
```

### Re-run a specific bulletin (e.g. to fix empty scripts or wrong audio duration)
```bash
uv run modal run modal_etl/run_batch.py --stem "PAGASA_25-TC22_Verbena_TCB#24" --force
```

`--stem` targets a single bulletin by its full stem (keep the `#` — the ETL sanitises it internally for storage paths).  
`--force` overwrites existing DB rows and Storage files even if already marked `ready`.
