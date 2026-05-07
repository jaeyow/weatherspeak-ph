# When the Storm Hits, English Isn't Enough
### WeatherSpeak PH — AI-powered multilingual typhoon warnings for the Philippines

---

## 1. The Hook — A Problem That Feels Personal

Picture a fishing village on the Visayas coast. Typhoon Pepito is making landfall. The wind is already bending the coconut palms sideways, and somewhere in Manila, PAGASA has issued Severe Weather Bulletin #1 — the official word on where the storm is going, how strong it is, and who needs to evacuate.

The bulletin exists. It's public. But it's written in English.

That's not a minor inconvenience. The Philippine Statistics Authority's own survey puts functional literacy — the ability to read, write, and comprehend — at 91.6%, which sounds high until you do the math: that's around 8 to 9 million Filipinos who can't reliably make sense of a written document. And English is a language most Filipinos encounter in school, not in daily life. A typhoon bulletin is a formal, technical document. For most people in coastal Cebu, it might as well be in another language entirely — because it is.

I'm Cebuano. I know this problem personally, not as an abstract policy issue but as something that plays out in places like San Remigio — a fishing town on the northern tip of Cebu, where the sea is right there and the storm surge risk is real. The people in that barangay aren't disconnected. They have phones. There's a TV in the sari-sari store. The technology isn't the gap. The language is. A PAGASA bulletin written in English is, for many people in that town, simply not a document they can use — whether because English isn't their everyday language, or because formal written text in any language isn't how they receive information. I'm not going to cite a number I'm not sure of. I'll just say: the bulletin exists for someone, and that someone isn't them.

That's the gap **WeatherSpeak PH** tries to close. It takes any PAGASA bulletin, runs it through an AI pipeline, and produces spoken audio in Cebuano, Tagalog, and English — in under five minutes.

---

## 2. The Idea — Why Gemma 4 Makes This Possible Now

Here's the thing about PAGASA bulletins: they're boring, in the best possible way. Every bulletin follows a similar structure — storm position, intensity, wind speed, signal levels, affected areas, storm track. It's a predictable schema, issued on a predictable schedule, in a predictable format. That's exactly the kind of problem a small, fast language model handles well.

One capability that made the whole family worth betting on: every Gemma 4 model is multimodal. That's not incidental — it's load-bearing. PAGASA bulletins include a storm track chart, a map showing where the cyclone is heading. Text extraction tools are blind to it. Gemma 4 can see it, and with the right prompt, describe it in plain language: "270 km northwest of Pag-asa Island, moving west-northwest at 20 km/h." That image-to-text step is what makes the radio script actually useful.

I started with **Gemma 4 26B**. It produces beautiful translations. It also took long enough to run that I'd have missed the hackathon deadline. So I dropped to **Gemma 4 E4B** — the 4-billion-parameter variant — and found that for structured document extraction and translation, the quality gap was smaller than I expected. E4B is fast enough to run locally via **Ollama** and on an A10G GPU in production. That tradeoff decided the whole project.

The audio side went through the same kind of pragmatic pivot. The original plan was Google Cloud Text-to-Speech — managed, reliable, easy. Then I realised: Google Cloud TTS has no Cebuano voice. So I ended up with two open-source models doing different jobs: **Facebook MMS TTS** handles Cebuano and Tagalog, and **Coqui XTTS v2** handles English, where it sounds noticeably more natural. I'll explain the phoneme hack that makes the Filipino languages work in Step 3.

At the center of it all is **Gemma 4 E4B** — doing the OCR interpretation, the storm chart reading, the English script generation, and the Cebuano and Tagalog translations. Every meaningful inference in this pipeline runs through it. The rest of the stack — Ollama, Facebook MMS, Coqui — exists to support that core. The result is a pipeline built entirely on open weights and open source, with no proprietary API calls for inference. That's not an ideological choice. It's a practical one: a community warning system can't depend on a paid API going offline during a typhoon.

---

## 3. The Build — Four Steps, Many Surprises

### Step 1 — Getting Text Out of a PDF

My first attempt was PaddleOCR. It kernel-crashed on macOS the same day I installed it. Next was Surya — good text extraction, completely blind to the storm track chart. I ended up on a hybrid: **Marker PDF** for the text and tables, **Gemma 4 E4B vision** for the chart. The chart is where Gemma 4's multimodal capability earns its place — given the image, it describes the storm's position in plain landmark language rather than coordinates. That took prompt work. Left to its own devices, the model outputs "13.9°N, 112°E." Nobody in San Remigio knows where that is.

### Step 2 — From Bulletin to Radio Script

The goal isn't translation — it's a community radio announcement. I generate an English script first, then translate Tagalog and Cebuano from that, not from the raw OCR. This produced better results, but the hallucination problem was real. Gemma 4 E4B was inventing wind speeds and wrong positions. The culprit: Marker was rendering a footnote tag as `<sup>75</sup>`, which the model read as "75 knots," and a stray coordinate row was being mistaken for the storm's current position. The fix was a two-layer clean: strip the noise before the LLM sees it, and reinforce constraints in the prompt. I also stripped the complex PAGASA signal tables entirely — the 4B model hallucinates badly when it can't parse nested markdown.

### Step 3 — Text to Speech in Languages Nobody Trained For

Cebuano has no commercial TTS voice — no Google, no Amazon, no Azure support. But **Facebook MMS** was trained on thousands of hours of multilingual Bible recordings, including Tagalog and Cebuano. It's the best option available for those languages, and it works — with caveats. MMS doesn't understand capitalisation or punctuation, so the TTS input has to be fully lowercased, and English words embedded in a Cebuano or Tagalog script need phonetic respelling to come out right. The script generation step accounts for all of that. English runs through **Coqui XTTS v2**, which handles punctuation and casing naturally and sounds noticeably more polished — a gap that quietly illustrates the problem this project is trying to solve.

### Step 4 — Getting It Live

The pipeline runs on **Modal** — serverless GPU for OCR and vision inference, CPU for translation and TTS, then a Supabase upload. Two flags worth mentioning: `--stem` targets a single bulletin for reprocessing, and `--force` overwrites existing records without touching the rest of the archive. That surgical re-run capability saved me hours when fixing hallucination bugs mid-batch. On the database side, a single `storms_with_status` view joins bulletins and media file paths — the frontend resolves public audio URLs directly from those storage paths.

---

## 4. The Frontend — Mobile-First Because the User Has a Phone, Not a Laptop

The target user is on a cheap Android handset in a coastal barangay, not at a desk. Every design decision followed from that. The play button is 64px — impossible to miss with a thumb. The layout is audio-first: the bulletin text is there if you want it, but the point is the speaker icon. A language toggle lets you switch between Cebuano, Tagalog, and English with one tap, and the audio reloads automatically.

Onboarding asks for province and municipality, plus your preferred language — Cebuano, Tagalog, or English. Right now the language selection drives everything: which audio plays, which script is shown. The location groundwork is laid for future personalisation. The whole thing is a mobile-first web app. You can also download the MP3 directly — so if you have signal now but might not later, you can save the audio for offline playback. That matters on the coast.

![Onboarding screen](01-onboarding.png)
![Active storm card](02-main-page-with-active-storm.png)
![Storm detail with audio player](03-storm-detail-with-audio-player.png)

---

## 5. What Gemma 4 Gets Right — and Where It Struggles

The original plan was to use Gemma 4 E4B for everything — including OCR. That didn't survive contact with real bulletins. The hallucinations were too frequent: invented numbers, misread tables, positions that didn't exist. I backtracked and handed OCR to **Marker**, a Surya-based PDF extractor that faithfully reproduces the document text without embellishment. That freed Gemma 4 E4B to do what it actually does well: reading the storm track chart, translating the cleaned text into Cebuano and Tagalog radio scripts, and generating the phonetic respellings that Facebook MMS needs for TTS.

In those roles it's reliable. Given clean input, a predictable schema, and a careful prompt, it follows style constraints well — km/h only, landmark-based positions, target word count. Where it still struggles is noisy context: stray OCR artefacts, complex nested tables, long prompts that trigger repetition. The lesson: scope the model tightly, clean the input aggressively, and don't ask a 4B model to do more than it needs to.

---

## 6. What It Can Do Right Now

Any PAGASA bulletin PDF goes in; Cebuano, Tagalog, and English audio comes out — end-to-end in around four minutes on Modal. Getting here took eleven Jupyter notebooks of experimentation — OCR comparisons, model evaluations, TTS trials — before a single line of production code was written. The pipeline has been through 33 pull requests of iteration across OCR, translation, TTS, ETL, and the frontend. The storm archive is live and browsable, audio is playable from any mobile browser, and every bulletin can be downloaded as an MP3.

---

## 7. What Comes Next

Right now the ETL pulls bulletin PDFs from a GitHub archive — it works, but it's manual. The real next step is live PAGASA ingestion: watch the feed, trigger the pipeline automatically when a new bulletin drops, no human in the loop. After that: testing Gemma 4 26B now that the pipeline is stable, to see whether the larger model meaningfully improves translation quality. Longer term — more languages. Ilocano, Waray, Hiligaynon, as many as are needed. Translation is essentially free once the pipeline exists; the main cost is hosting. The harder problem is TTS — low-resource languages have few good options, and that's not something one project can fix alone.

---

## 8. The Close — Why It Matters

Come back to San Remigio. The storm is coming. The PAGASA bulletin exists. But now the barangay captain has a phone, and on that phone is an audio file in Cebuano — generated in four minutes from the same PDF, by a pipeline built by one developer in a few weeks using an open-weight model anyone can run.

Digital equity isn't about giving people smartphones. Most of them already have one. It's about making the information on those phones actually useful — in the language they think in, in the voice they trust. Gemma 4 made that tractable. The code is open source, the model is open weight, and nothing here is specific to the Philippines. Any language, any country, any disaster alert system.

---
