# When the Storm Hits, English Isn't Enough
### WeatherSpeak PH — AI-powered multilingual typhoon warnings for the Philippines

---

## 1. The Hook — A Problem That Feels Personal

Picture San Remigio, on the northern coast of Cebu. Typhoon Verbena is on a direct track toward the island. The wind is already bending the coconut palms sideways, and somewhere in Manila, PAGASA has issued a Tropical Cyclone Bulletin — the official word on where the storm is going, how strong it is, and who needs to evacuate.

The bulletin exists. It's public. But it's written in English.

That's not a minor inconvenience. The Philippine Statistics Authority puts functional literacy — the ability to read, write, and comprehend — at 91.6%. That sounds high until you do the math: around 8 to 9 million Filipinos who can't reliably make sense of a written document. And English is a language most Filipinos encounter in school, not in daily life. A typhoon bulletin is a formal, technical document. For most people in coastal Cebu, it might as well be in another language — because it is.

I'm Cebuano. I know this problem personally — not as an abstract policy issue but as something playing out right now in that town. The people in San Remigio aren't disconnected. They have phones. There's a TV in the sari-sari store. The technology isn't the gap. The language is.

That's the gap **WeatherSpeak PH** tries to close. It takes any PAGASA bulletin, runs it through an AI pipeline, and produces both readable scripts and spoken audio in Cebuano, Tagalog, and English — in under five minutes.

---

## 2. The Idea — Why Gemma 4 Makes This Possible Now

Here's the thing about PAGASA bulletins: they're boring, in the best possible way. Every bulletin follows the same structure — storm position, intensity, wind speed, signal levels, affected areas, storm track. It's a predictable schema, issued on a predictable schedule. That's exactly the kind of problem a small, fast language model handles well.

Every Gemma 4 model is multimodal — and that's load-bearing here. PAGASA bulletins include a storm track chart that text extraction tools are blind to. Gemma 4 can see it, and with the right prompt, describe it in plain language: "270 km northwest of Pag-asa Island, moving west-northwest at 20 km/h." That image-to-text step is what makes the radio script actually useful.

I started with **Gemma 4 26B** — beautiful translations, too slow for the hackathon timeline. I dropped to **Gemma 4 E4B** and found the quality gap smaller than expected for structured document work. Fast enough for local Ollama inference and an A10G GPU in production. That tradeoff decided the whole project.

The audio side hit the same wall. Google Cloud TTS has no Cebuano voice. Solution: **Facebook MMS TTS** for Cebuano and Tagalog, **Coqui XTTS v2** for English — more natural-sounding on its native language.

At the center is **Gemma 4 E4B** — handling chart reading, script generation, and all three language translations. Open weights, open source, no proprietary inference APIs — because a community warning system can't depend on a paid service going offline during a typhoon.

---

## 3. The Build — Four Steps, Many Surprises

### Step 1 — Getting Text Out of a PDF

My first attempt was PaddleOCR. It kernel-crashed on macOS the same day I installed it. Next was Surya — good text extraction, completely blind to the storm track chart. I ended up on a hybrid: **Marker PDF** for the text and tables, **Gemma 4 E4B vision** for the chart. Given the image, it describes the storm's position in plain landmark language. Left to its own devices, it outputs coordinates. Nobody in San Remigio knows where 13.9°N, 112°E is.

### Step 2 — From Bulletin to Radio Script

The goal isn't translation — it's a community radio announcement. I generate English first, then translate Tagalog and Cebuano from that. The hallucination problem was real: Gemma 4 E4B was inventing wind speeds. The culprit — a footnote tag Marker rendered as `<sup>75</sup>` that the model read as "75 knots," plus a stray coordinate row mistaken for the storm's current position. Fix: strip the noise before the LLM sees it, reinforce constraints in the prompt, and strip the complex PAGASA signal tables entirely — the 4B model hallucinates badly on nested markdown.

### Step 3 — Text to Speech in Languages Nobody Trained For

No commercial TTS exists for Cebuano. **Facebook MMS**, trained on multilingual Bible recordings, is the best available — and it works, with caveats: it doesn't understand capitalisation or punctuation, so input must be fully lowercased, and English words need phonetic respelling. The script generation step handles all of that. English goes through **Coqui XTTS v2**, which handles casing and punctuation natively and sounds noticeably more polished — a gap that quietly illustrates this project's entire premise.

### Step 4 — Getting It Live

The pipeline runs on **Modal** — GPU for OCR and vision, CPU for translation and TTS, then a Supabase upload. Two flags: `--stem` targets a single bulletin, `--force` overwrites it without touching the archive. That surgical re-run saved hours when fixing bugs mid-batch. A single `storms_with_status` database view is all the frontend queries.

---

## 4. The Frontend — Mobile-First Because the User Has a Phone, Not a Laptop

The target user is on a cheap Android handset, not at a desk. Every design decision follows from that: 64px play button, audio-first layout, one-tap language toggle between Cebuano, Tagalog, and English.

Onboarding collects province, municipality, and language preference. Right now language drives everything — which audio plays, which script is shown — with location wired up for future personalisation. You can download the MP3 for offline playback, which matters where mobile data is intermittent.

![Onboarding screen](01-onboarding.png)
![Active storm card](02-main-page-with-active-storm.png)
![Storm detail with audio player](03-storm-detail-with-audio-player.png)

---

## 5. What Gemma 4 Gets Right — and Where It Struggles

The original plan was to use Gemma 4 E4B for everything — including OCR. That didn't survive contact with real bulletins. Hallucinations were too frequent: invented numbers, misread tables, positions that didn't exist. I backtracked and handed OCR to **Marker**, a Surya-based PDF extractor that faithfully reproduces document text without embellishment. That freed Gemma 4 E4B for what it actually does well: reading the storm track chart, translating cleaned text into Cebuano and Tagalog radio scripts, and generating the phonetic respellings Facebook MMS needs for TTS.

In those roles it's reliable. Given clean input, a predictable schema, and a careful prompt, it follows style constraints well — km/h only, landmark-based positions, target word count. Where it still struggles is noisy context: stray OCR artefacts, complex nested tables, long prompts that trigger repetition. The lesson: scope the model tightly, clean the input aggressively, and don't ask a 4B model to do more than it needs to.

---

## 6. What It Can Do Right Now

Any PAGASA bulletin PDF goes in; Cebuano, Tagalog, and English audio comes out — end-to-end in around four minutes on Modal. Getting here took eleven Jupyter notebooks of experimentation — OCR comparisons, model evaluations, TTS trials — before a single line of production code was written. The pipeline has been through 33 pull requests of iteration across OCR, translation, TTS, ETL, and the frontend. The storm archive is live and browsable, audio is playable from any mobile browser, and every bulletin can be downloaded as an MP3.

---

## 7. What Comes Next

Right now the ETL pulls bulletin PDFs from a GitHub archive — it works, but it's manual. The real next step is live PAGASA ingestion: watch the feed, trigger the pipeline automatically when a new bulletin drops. After that: testing Gemma 4 26B now that the pipeline is stable, to see whether the larger model meaningfully improves translation quality. Longer term — more languages. Ilocano, Waray, Hiligaynon, as many as are needed. Translation is essentially free once the pipeline exists; the main cost is hosting. The harder problem is TTS — low-resource languages have few good options, and that's not something one project can fix alone.

---

## 8. The Close — Why It Matters

Come back to San Remigio. The storm is coming. The PAGASA bulletin exists. But now the barangay captain has a phone, and on that phone is an audio file in Cebuano — generated in four minutes from the same PDF, by a pipeline built by one developer in a few weeks using an open-weight model anyone can run.

Digital equity isn't about giving people smartphones. Most of them already have one. It's about making the information on those phones actually useful — in the language they think in, in the voice they trust. Gemma 4 made that tractable. The code is open source, the model is open weight, and nothing here is specific to the Philippines. Any language, any country, any disaster alert system.

---
