Picture [Ronda, on the southwestern coast of Cebu, Philippines](https://en.wikipedia.org/wiki/Ronda,_Cebu). Typhoon [Verbena](https://www.rappler.com/philippines/weather/tropical-storm-verbena-shear-line-update-pagasa-forecast-november-26-2025-2am/) is bearing down on the island. [PAGASA](https://en.wikipedia.org/wiki/PAGASA) has issued a Tropical Cyclone Bulletin: the official word on where the storm is going, how strong it is, and who needs to evacuate.

The bulletin exists. It's public. But it's written in English.

The Philippines averages 20 typhoons a year. Each arrives with a bulletin like this and costs lives, livelihoods, and billions in damage.

![](https://www.googleapis.com/download/storage/v1/b/kaggle-forum-message-attachments/o/inbox%2F1940847%2F12738810386e63bfddeb28398bd81314%2Fpagasa-25-TC22_PAGASA_25-TC22_Verbena_TCB24.png?generation=1778920500039187&alt=media)

The Philippine Statistics Authority puts functional literacy at 91.6%. In a country of 115 million people, that's nearly 10 million Filipinos who can't reliably make sense of a written document. For most people on that coast, the bulletin might as well be in another language. Because it is.

I'm [Cebuano](https://en.wikipedia.org/wiki/Cebuano_language). I know this problem personally, not as a statistic but as something playing out right now in that town. They have phones. There's a TV in the sari-sari store. **The technology isn't the gap. The language is**.

That's the gap **WeatherSpeak PH** closes: PAGASA bulletins in Cebuano, [Tagalog](https://en.wikipedia.org/wiki/Tagalog_language), and English, with audio, in only a few minutes.

## How Can [Gemma 4](https://deepmind.google/models/gemma/gemma-4/) Possibly Help?

Every PAGASA bulletin follows the same structure: storm position, intensity, wind speed, signal levels, affected areas, storm track. Exactly the kind of problem a small, fast language model handles well.

Every Gemma 4 model is multimodal. PAGASA bulletins include a storm track chart that text extraction tools are blind to. Gemma 4 can see it and describe it in plain language. That image-to-text step is what makes the radio script useful.

I started with **Gemma 4 26B**: beautiful translations, but too slow for notebook-driven experimentation. I dropped to **Gemma 4 E4B** and found the quality gap smaller than expected.

## Nothing Worked the First Time

### Step 1: The Faithful Extraction Problem

My first instinct was to use **Gemma 4 E4B** for everything: feed it the PDF, get structured output back. It hallucinated badly. The problem was faithfulness: it wasn't reproducing the bulletin text as written, it was paraphrasing and sometimes inventing. Back to the notebooks. [**Marker PDF**](https://pypi.org/project/marker-pdf/) turned out to be near-perfect at faithful text extraction, reproducing the bulletin content exactly as it appeared on the page. But Marker was blind to the storm track chart. **Gemma 4 E4B** could read that chart and describe the storm's position in plain landmark language. Left to its own devices, it outputs coordinates. Nobody in Ronda knows where 13.9°N, 112°E is. The hybrid was the answer: **Marker for text, Gemma 4 for the chart**.

### Step 2: Garbage In, Hallucination Out

The goal isn't just translation. It's a community radio announcement. My first attempt generated all three languages in parallel directly from the [OCR](https://en.wikipedia.org/wiki/Optical_character_recognition). The problem: they diverged. English came out consistently richer and more faithful to the source. The model simply performs better in English.

The fix: generate English first, then translate Tagalog and Cebuano from that. The local language scripts are now only as wrong as the English one, which is a much smaller problem.

Hallucinations were a separate fight. Gemma 4 E4B was inventing wind speeds: a footnote tag Marker rendered as `<sup>75</sup>` that the model read as "75 knots," and a stray coordinate row it mistook for the storm's current position.

The fix: strip the noise before the model sees it, tighten the prompt constraints, and strip the markdown signal tables. Similar province/signal data appears in plain prose above the tables, so not much information is lost, just the nested markdown the 4B model chokes on.

### Step 3: Text to Speech (TTS) Bible Recordings to the Rescue

[**Coqui XTTS v2**](https://huggingface.co/coqui/XTTS-v2) supports English natively, and Tagalog and Cebuano through a Spanish phoneme approximation. The problem was quality: when I heard the Tagalog and Cebuano output, it was bad enough to rule out. That led to [**Facebook MMS**](https://research.facebook.com/publications/scaling-speech-technology-to-1000-languages/), trained by Meta, including those of multilingual Bible recordings. The way it speaks Cebuano and Tagalog, though not perfect, is noticeably better. The choice was also deliberate: self-hostable, open weights, runs on a GPU I control, no per-character billing, no vendor lock-in. Better commercial options probably exist. I'd rather own the stack.

MMS comes with caveats that had real [ETL](https://en.wikipedia.org/wiki/Extract,_transform,_load) consequences. It doesn't understand capitalisation or punctuation, so every script needs pre-processing before it reaches the model: lowercase everything, strip punctuation, and phonetically respell any English words that slip through. Building that pre-processing step into the pipeline was non-trivial, for example:
- forecast → por-kast
- evacuation → i-ba-kyu-we-syon
- coastal → kos-tal.

Speed tuning was its own problem. The MMS voices speak at different natural rates, so each language needed separate calibration: Cebuano at 1.40×, Tagalog at 1.35×. At 1.5×, Cebuano sounds like a chipmunk.

English stays on **Coqui XTTS v2**, where it handles casing and punctuation natively and sounds noticeably more polished. The contrast in quality between the English and Cebuano/Tagalog audio is real. It's an uncomfortable reminder of why this project exists.

### Step 4: Ollama, Modal, and a Single Command

I built the pipeline on [**Modal**](https://modal.com/) with compute matched to each step: OCR and script generation on A10G GPU, three parallel TTS containers for Cebuano, Tagalog, and English, then a CPU container for the [Supabase](https://supabase.com/) upload.

One architectural decision made everything easier: the pipeline code is fully modular, and the same modules run in both the **ETL** and the **Jupyter notebooks**. When I iterate on a prompt in a notebook, the output is identical to what the production ETL produces. There's no "works in the notebook, breaks in production" problem. The notebook and the ETL are running the same code.

[**Ollama**](https://ollama.com/) runs Gemma 4 E4B in both environments: 
- locally during notebook iteration
- on Modal's A10G in production. 

Same API, same model weights, different hardware. That's what keeps the notebook and ETL outputs identical.

[![ETL on Modal.com](https://storage.googleapis.com/kaggle-forum-message-attachments/3434826/42824/Gemma%20E4B%20OCR%20to%20Speech-2026-05-16-121947.png)](https://storage.googleapis.com/kaggle-forum-message-attachments/3434826/42824/Gemma%20E4B%20OCR%20to%20Speech-2026-05-16-121947.png)

Modal also removed the need for any orchestration or triggering infrastructure. No scheduler, no cron job, no cloud VM sitting idle. The trigger is a single command from my laptop: `uv run modal run modal_etl/run_batch.py`. Modal provisions the GPU, runs the pipeline, and tears down. All the compute is in the cloud; the trigger is local, it's a hackathon project after all.

Script generation originally ran all three languages sequentially: one container, one Ollama instance, **~4 minutes** wall time. Refactoring to one container per language brought that down to **~1.5 minutes**.

When a bulletin came out with the wrong wind speed, I didn't want to reprocess the entire archive. So I built two flags: `--stem` to target a single bulletin by name, `--force` to overwrite existing outputs.

## Gemma 4: Strengths and Limits

Building all of that taught me where Gemma 4 E4B is reliable: clean inputs, predictable schema, clear prompt, no noise. It follows style constraints well, reads a storm chart, and does all of this at E4B speed.

Where it falls down is noisy context. Stray OCR artefacts, complex nested tables, long prompts that trigger repetition. Any of these cause hallucinations. The fix is upstream: clean the input, scope the task.

**Fine-tuning is the obvious next lever**. It is beyond the scope of this project.

## A Mobile-First Web Application

The target user is on a cheap mobile handset. Application written with [Next.js](https://nextjs.org/) hosted on [Vercel](https://vercel.com/). Every design decision follows: 64px play button, audio-first layout, one-tap language toggle.

>The first time I switched the toggle to Cebuano and hit play, and heard a typhoon warning come out in the language my Lola speaks, that was the moment the whole project felt real. That's what this is for.

Language drives everything: which audio plays, which script is shown. Offline **MP3 download** is supported for where mobile data is intermittent.

![Storm detail with audio player](https://www.googleapis.com/download/storage/v1/b/kaggle-forum-message-attachments/o/inbox%2F1940847%2F9413fd23ab1b016ba37d6aeba5aadf1a%2Fcebu-verbena-audio-3.png?generation=1778334500575778&alt=media)

## What It Can Do Right Now

Any PAGASA bulletin PDF goes in. Cebuano, Tagalog, and English radio scripts and audio come out, end-to-end in a few minutes.

Eleven notebooks and 40 pull requests later. [The storm archive is live, and audio is playable from any mobile browser.](https://weatherspeak-ph.vercel.app/)

## What Comes Next

Next, I'll add live PAGASA ingestion, triggering automatically when a new bulletin drops. I'll also test Gemma 4 26B to see if the quality gain justifies the cost.

Longer term: Ilocano, Waray, Hiligaynon and 180+ other dialects. Adding a new dialect is a prompt change. TTS is the bottleneck. Low-resource dialects have only a few options, and that's bigger than this project.

## Why It Matters

Typhoon Verbena is still on track towards southwestern Cebu. The PAGASA bulletin exists. So does an audio file in Cebuano, generated in a few minutes by a batch pipeline on a cloud GPU, ready to play on my Lola's phone.

Digital equity isn't about giving people smartphones. Most already own one. It's about making the information on those phones useful in the language they think in. [The code](https://github.com/jaeyow/weatherspeak-ph) and models used are open source, and nothing here is specific to the Philippines.

The principles we used here can be applied with any language, any country, any disaster alert system.