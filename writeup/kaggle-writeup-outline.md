# WeatherSpeak PH — Kaggle Write-up Outline

**Working title:** *"When the Storm Hits, English Isn't Enough"*
**Tone:** First-person narrative; builder's journal. Not a technical report.
**Target:** Kaggle community + hackathon judges. Assumes some ML familiarity but no Philippines context.

---

## 1. The Hook — A Problem That Feels Personal

- Open with a concrete scene: a typhoon making landfall, a fishing village on the Visayas coast, a PAGASA bulletin nobody can read
- PAGASA issues all typhoon warnings in English — a language only ~15% of Filipinos use fluently day-to-day
- The communities most at risk (coastal fisherfolk, rural farmers) are also the least served by English-only systems
- One sentence on what WeatherSpeak PH does: *converts any PAGASA bulletin into spoken Cebuano, Tagalog, and English audio in under 5 minutes*

---

## 2. The Idea — Why Gemma 4 Makes This Possible Now

- The insight: PAGASA bulletins are structured PDFs with a predictable schema — perfect for a small, fast model
- Why Gemma 4 E4B specifically: multimodal (text + vision), runs locally via Ollama, fast enough for real-time processing on an A10G GPU
- The original plan: Gemma 4 26B for quality, Google Cloud TTS for audio
- Why the plan changed: 26B was too slow for hackathon timelines; E4B hit the right speed/quality tradeoff; Coqui XTTS v2 replaced Google TTS

---

## 3. The Build — Four Steps, Many Surprises

A walk through the ETL pipeline as it actually evolved, not the clean version.

### Step 1 — Getting Text Out of a PDF (Harder Than It Sounds)

- First attempt: PaddleOCR → kernel crash on macOS, abandoned same day
- Tried Surya → good text, blind to the storm track chart
- Settled on a hybrid: **Marker PDF** for accurate table/text extraction + **Gemma 4 vision** for the storm track chart
- The chart matters: it shows where the storm is going, and the model needed to describe it in plain language for the radio script
- Prompt engineering the chart description: getting Gemma 4 to say "270 km northwest of Pag-asa Island" instead of "13°N, 112°E"

### Step 2 — From Bulletin to Radio Script

- The translation problem: not word-for-word translation — it needs to sound like a community radio announcement
- English-first strategy: generate EN script, then translate TL and CEB from EN (not from the raw OCR)
- The hallucination war: Gemma 4 E4B inventing wind speeds, wrong positions, looping output
  - Root cause 1: Marker's `<sup>75</sup>` footnote tag rendered as "75 knots"
  - Root cause 2: Stray `13.9 108.7 685 km West Northwest` coordinate row picked up as current position
  - Fix: two-layer approach — clean the OCR *before* the LLM sees it + reinforce in the prompt
- Table stripping: PAGASA signal tables are complex nested markdown; 4B model hallucinates when it can't parse them; stripping tables and relying on prose sections above them solved it

### Step 3 — Text to Speech in Languages Nobody Trained For

- Cebuano has no production TTS model (as of 2025)
- The phoneme hack: XTTS v2 doesn't know Cebuano, but Spanish phoneme rules produce intelligible Cebuano audio
- Same trick for Tagalog (`es` phonemes as the closest approximation)
- English uses the native `en` voice — sounds noticeably better, which itself tells a story about the language gap

### Step 4 — Getting It Live

- Modal for serverless GPU inference: Step 1 (A10G), Steps 2–3 (CPU), Step 4 (Supabase upload)
- The `--stem` and `--force` flags: surgical re-runs without reprocessing the whole archive
- Supabase PostgreSQL + Storage: bulletins, media rows, signed URLs
- `storms_with_status` view: drives the frontend with a single query

---

## 4. The Frontend — Mobile-First Because the User Has a Phone, Not a Laptop

- Who uses this: people on cheap Android handsets in coastal barangays, not desktop users
- Design decisions that followed from that: large play button (64px), audio-first layout, no dense tables
- Language toggle: switch between CEB / TL / EN with one tap, audio re-loads automatically
- Location onboarding: province → city, used to calculate storm distance and personalise warnings
- The PWA: installable, works with intermittent connectivity
- Screenshot tour: onboarding → storm list → storm detail → audio player → track map

---

## 5. What Gemma 4 Gets Right (and Where It Struggles)

An honest appraisal — what worked and what required workarounds.

**What it gets right:**
- Structured extraction from predictable document schemas
- Multimodal chart + text grounding when prompted carefully
- Natural, community-friendly translations at E4B speed
- Following detailed style constraints (km/h only, landmark-based locations, word count targets)

**Where it struggled:**
- Complex nested tables at 4B parameter scale: hallucination under table-parsing failure
- OCR artefacts in the context window: model misreads noisy text as signal
- Coordinates vs. landmarks: needed explicit prompt rules to stop outputting degrees
- Consistency under long prompts: repeat-penalty side-effects, temperature tuning

---

## 6. What It Can Do Right Now

- Processes any PAGASA bulletin PDF end-to-end in ~4 minutes on Modal
- Produces spoken audio in Cebuano, Tagalog, and English
- Covers 33 PRs of iteration across OCR, translation, TTS, ETL, and frontend
- Live at [URL] — storm history browsable, audio playable from any mobile browser

---

## 7. What Comes Next

- Real-time ingestion: watch the PAGASA RSS feed, trigger ETL automatically on new bulletins
- Gemma 4 26B quality test: now that the pipeline is stable, test whether 26B meaningfully improves translation naturalness
- Cebuano community TTS: a trained Coqui model would replace the Spanish-phoneme hack
- More languages: Ilocano, Waray, Hiligaynon — the Philippines has 180+ languages
- NDRRMC integration: not just PAGASA; local government disaster bulletins too

---

## 8. The Close — Why It Matters

- Come back to the opening scene: the same fishing village, but now the barangay captain can play the Cebuano audio on a loudspeaker
- Digital equity isn't about giving everyone a smartphone — it's about making the information on those phones actually useful
- Gemma 4 made this project tractable for one developer in five weeks
- The code is open source; the model is open weight; anyone can run a version of this for any language, any country, any disaster alert system

---

*Screenshots: `writeup/01-onboarding.png` through `writeup/11-mobile-storm-detail.png`*
