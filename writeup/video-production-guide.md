# WeatherSpeak PH — Video Production Guide

A step-by-step guide to recording and editing your 3-minute Kaggle hackathon video using OBS and iMovie.

---

## The Script

Target pace: **2.5–2.8 words per second** — energetic but not rushed. Scenes 14 and 15 are intentionally slower with deliberate pauses between sentences.

Total runtime: ~2:22

---

### Scene 1 — Philippines typhoons (9.9s)
**Tool: iMovie** — stock footage or satellite video. No recording needed.
**Source:** pexels.com ("typhoon"), pixabay.com ("storm waves"), or NASA's YouTube channel ("NASA typhoon satellite" — public domain).

> Every year, 20 typhoons hit the Philippines. Each one costs lives, livelihoods, and billions in damage. When a storm comes, people need to know — fast.

---

### Scene 2 — The PAGASA Bulletin PDF (6.7s)
**Tool: iMovie** — screenshot of the bulletin with Ken Burns pan. Use `Cmd+Shift+4` to capture.
**Ken Burns tip:** Start wide on the full bulletin, end zoomed in on the storm position line.

> PAGASA issues a bulletin with every storm — position, intensity, evacuation zones. But it's written in English.

---

### Scene 3 — Coastal drone shot 1 (5s)
**Tool: iMovie** — downloaded stock footage.
**Source:** pexels.com ("Philippines coast drone") or pixabay.com ("coastal village aerial").

> For millions of Filipinos on these coasts, that bulletin might as well not exist.

---

### Scene 4 — Coastal drone shot 2 (5s)
**Tool: iMovie** — downloaded stock footage. Continues from Scene 3.

> They have phones. The technology isn't the gap. The language is.

---

### Scene 5 — ETL on Modal.com (6.1s)
**Tool: iMovie** — still image (`05-etl-pipeline.png`). No recording needed.

> Powered by Gemma 4, running on Modal. It reads the bulletin, reads the storm chart, and generates audio. Four minutes.

---

### Scene 6 — Introducing WeatherSpeak PH (6.5s)
**Tool: iMovie** — screenshot of the WeatherSpeak PH main page.

> This is WeatherSpeak PH. Any PAGASA bulletin goes in. Cebuano, Tagalog, and English audio comes out.

---

### Scene 7 — Onboarding location (11.2s)
**Tool: OBS** — screen recording of the location onboarding flow.

> The app asks for your location once. From there, it calculates how far every active storm is from where you are — shown on every storm card.

---

### Scene 8 — Main page navigation (8.1s)
**Tool: OBS** — screen recording of the main storm list page. Navigate slowly and deliberately.

> Active storms at the top, past storms below. One tap takes you to the full bulletin with audio ready in three languages.

---

### Scene 9 — English bulletin (16.4s)
**Tool: OBS** — screen recording with system audio. Click play on English audio and let it run.
**No narration.** Let the English bulletin audio speak for itself.

---

### Scene 10 — Introducing Tagalog bulletin (6.6s)
**Tool: OBS** — continue screen recording. Switch language toggle to Tagalog.

> That's English. Same bulletin, same storm, now in Tagalog — translated by Gemma 4 from the English script.

---

### Scene 11 — Tagalog bulletin (18.2s)
**Tool: OBS** — screen recording with system audio. Click play on Tagalog audio and let it run.
**No narration.**

---

### Scene 12 — Introducing Cebuano bulletin (5.5s)
**Tool: OBS** — continue screen recording. Switch language toggle to Cebuano.

> And this is Cebuano — the language twenty million Filipinos call their own.

---

### Scene 13 — Cebuano bulletin (25.7s)
**Tool: OBS** — screen recording with system audio. Click play on Cebuano audio and let it run.
**No narration.**

---

### Scene 14 — Last look of WeatherSpeak PH (6.5s)
**Tool: iMovie** — screenshot of the main page or bulletin detail page.
**Deliver each sentence as its own beat with a pause after it.**

> Same bulletin. Four minutes. Three languages. Open source. Playable on any phone.

---

### Scene 15 — Lola on her mobile phone (4.5s)
**Tool: iMovie** — stock photo.
**Source:** pexels.com — search "elderly woman phone" or "grandmother smartphone".
**Deliver each line slowly with a deliberate pause between them.**

> Any language. Any country. Any disaster alert system.

---

## Before You Record — Checklist

**Assets to download before recording:**
- [ ] Scene 1: typhoon satellite or stock footage (pexels.com, pixabay.com, or NASA YouTube)
- [ ] Scenes 3–4: coastal drone footage (pexels.com — "Philippines coast drone")
- [ ] Scene 15: photo of elderly woman using a phone (pexels.com — "grandmother smartphone")
- [ ] Background music track downloaded (see Step 7 in iMovie Editing)

**Screenshots to take before recording:**
- [ ] Scene 2: PAGASA Verbena bulletin PDF — `Cmd+Shift+4`
- [ ] Scene 6: WeatherSpeak PH main page
- [ ] Scene 14: WeatherSpeak PH main page or bulletin detail page

**OBS setup (for Scenes 7–13):**
- [ ] Browser tabs ready:
  - Tab 1: WeatherSpeak PH app — location onboarding
  - Tab 2: WeatherSpeak PH app — storm list page
  - Tab 3: Verbena bulletin detail page (English tab ready)
- [ ] Browser in full screen: `Cmd+Ctrl+F`
- [ ] Dock hidden: System Settings → Desktop & Dock → Automatically hide and show the Dock
- [ ] Microphone plugged in and working — check audio meter in OBS
- [ ] System audio capture working — play a sound and confirm OBS picks it up
- [ ] Phone on silent
- [ ] Door closed, room quiet
- [ ] Read the full script out loud at least twice before recording

---

## OBS Setup

### Step 1 — Install and open OBS
Download from obsproject.com if not already installed. Open it.

### Step 2 — Add sources
In the **Sources** panel at the bottom of the screen, click **+** and add:

1. **Display Capture** → select your monitor → click OK
   Your screen will appear in the OBS preview window.

2. **Audio Input Capture** → select your microphone
   Speak and confirm the audio meter at the bottom is moving.

### Step 3 — Configure settings
Go to **OBS menu → Settings**:

**Output tab:**
| Setting | Value |
|---|---|
| Recording Format | MPEG-4 (.mp4) |
| Video Encoder | Apple VT H264 Hardware Encoder |
| Audio Encoder | Core Audio AAC |
| Recording Path | Desktop (or a folder you'll remember) |

**Video tab:**
| Setting | Value |
|---|---|
| Base Resolution | 1920×1080 |
| Output Resolution | 1920×1080 |
| Frame Rate | 30 |

Click **OK** to save.

### Step 4 — Test before recording
Click **Start Recording**, say a few words, click **Stop Recording**. Find the file on your Desktop and play it back. Confirm your voice and screen are both captured.

---

## Recording Each Scene

Scenes 1–6 and 14–15 are assembled in iMovie from still images and downloaded footage — no recording needed. Only Scenes 7–13 require OBS.

| Take | Scenes | Tool | What to have on screen |
|---|---|---|---|
| Take 1 | 7 — Onboarding | OBS | Location onboarding screen |
| Take 2 | 8 — Main page | OBS | Storm list page — navigate slowly |
| Take 3 | 9–13 — Audio demo | OBS | Verbena bulletin detail page — play EN, TL, CEB in order |

**For each take:**
1. Get your browser into position
2. Take a breath
3. Click **Start Recording** in OBS
4. Speak and perform the on-screen actions
5. Click **Stop Recording**

**If you make a mistake:** Don't stop recording. Pause for two seconds, say "take two" out loud so you can find it in the edit, then start the sentence again from the beginning. iMovie will let you cut the mistake out.

**Tip:** Do at least two takes of every scene. You only need one good one.

---

## iMovie Editing

### Step 1 — Create a new project
Open **iMovie** (Launchpad or Applications folder).
Click **Create New → Movie**.

### Step 2 — Import your recordings
Click the **Import Media** button (down arrow icon, top left).
Select all your OBS mp4 files. They appear in the media browser at the top.

### Step 3 — Build the timeline
Drag your clips into the timeline at the bottom in scene order:
Take 1 → Take 2 → Take 3 → Take 4 → Take 5 → Take 6

### Step 4 — Trim clips
Each clip will have silence or fumbling at the start and end.

- Click a clip in the timeline
- Drag the **left yellow edge** rightward to remove the start
- Drag the **right yellow edge** leftward to remove the end

### Step 5 — Cut out a mistake in the middle
1. Click the clip containing the mistake
2. Move the white playhead line to just **before** the mistake
3. Press **Cmd+B** — this splits the clip
4. Move the playhead to just **after** the mistake
5. Press **Cmd+B** again
6. Click the middle piece (the mistake) and press **Delete**

### Step 6 — Add a title card
1. Click **Titles** in the top menu bar
2. Choose a simple style (e.g. **Lower Third** or **Centered**)
3. Drag it to the very beginning of the timeline
4. Type: `WeatherSpeak PH` on line 1
5. Type: `AI typhoon warnings in Cebuano, Tagalog & English` on line 2

### Step 7 — Add background music
Quiet background music significantly increases emotional impact.

**Free music sources (no copyright issues for YouTube):**
- **YouTube Audio Library** — studio.youtube.com → Audio Library. Filter by Cinematic or Inspirational. Everything is pre-cleared for YouTube.
- **Pixabay Music** — pixabay.com/music. Search "cinematic" or "atmospheric". Free, no attribution required.
- **Free Music Archive** — freemusicarchive.org. Filter by CC0 or CC BY licence.
- **Incompetech** — incompetech.com. All CC BY — credit Kevin MacLeod in your video description.

Look for something quiet and atmospheric, not a track with a strong beat or melody that competes with your voice.

**Adding to iMovie:**
1. Import the downloaded MP3: click the **Import Media** button and select the file
2. Drag it from the media browser to the timeline — it appears as a green bar underneath your clips
3. Click the green bar — a volume slider appears at the top of the clip
4. Drag the slider down to **15–20%** so it doesn't compete with your voice
5. To fade out at the end: right-click the green bar → **Show Audio** → drag the fade handle at the right edge inward

### Step 8 — Check your total length
The total duration is shown at the bottom right of the timeline. It must be **under 3:00**.

### Step 9 — Adjust audio (if needed)
If your voice is too quiet or the app audio is too loud:
- Click the clip
- Use the **volume slider** (speaker icon) in the top right of the screen

### Step 10 — Export
1. Go to **File → Share → File**
2. Set Resolution to **1080p**
3. Set Quality to **Better**
4. Set Format to **Video and Audio**
5. Click **Next**, save to Desktop
6. Wait for export to finish (2–5 minutes)

---

## Upload to YouTube

1. Go to **studio.youtube.com**
2. Click **Create → Upload Video**
3. Upload your exported file
4. Title: `WeatherSpeak PH — AI Typhoon Warnings in Cebuano, Tagalog & English`
5. Description: paste your Kaggle write-up summary or a short paragraph about the project
6. Set visibility to **Public** (not Private or Unlisted — judges must view without logging in)
7. Click **Save**
8. Copy the YouTube URL from your browser and paste it into your Kaggle submission

---

## Quick Tips

- **Take 3 (Scenes 9–13, the audio demo) is your most important OBS recording.** Spend the most time getting it right. Let each language play for its full duration — don't rush the switches.
- **Target 2.5–2.8 words per second.** That's energetic without feeling rushed. Scenes 14 and 15 are the exception — slow down and let the pauses land.
- **Don't re-record everything if one scene is bad.** Just re-record that one scene.
- **Natural light or a well-lit room** makes a big difference if your face is on camera. If you're only recording your screen, this doesn't matter.
- **YouTube auto-captions** will generate subtitles automatically after upload. Enable them in YouTube Studio before submitting — it helps judges who watch without sound.
