# Gemma 4 Good Hackathon - Project Plan
## WeatherSpeak PH: Multilingual Severe Weather Communications

---

## 🎯 The Problem

**Critical weather information is not accessible to millions of Filipinos.**

- PAGASA (Philippine Atmospheric, Geophysical and Astronomical Services Administration) issues severe weather bulletins and tropical cyclone reports **only in English**
- Documents are distributed as PDFs on file servers and websites
- **74+ Filipino languages/dialects spoken**, but weather warnings reach only English speakers
- During typhoons and severe weather, timely information in local languages can **save lives**
- Rural communities, elderly populations, and those with limited education are most at risk

### Real-World Impact
- Philippines experiences ~20 tropical cyclones annually
- Typhoon Haiyan (2013): 6,300+ deaths, partly due to communication barriers
- Many Filipinos consume information via radio/audio rather than text
- Internet connectivity is unreliable during storms - **local/offline solutions are critical**

---

## 💡 The Solution: WeatherSpeak PH

An AI-powered system using **Gemma 4** that:

1. **Parses** severe weather bulletins from PAGASA PDFs
2. **Translates** critical information into local Filipino dialects:
   - Tagalog
   - Bisaya/Cebuano
   - Ilocano
   - Kapampangan
   - Hiligaynon
   - Waray
   - (and more)
3. **Generates audio reports** like radio broadcasts in local languages
4. **Downloadable for offline playback** - users pre-download reports before storms hit  
5. **User-friendly interface** - select dialect, download and play weather report
6. **Phase 1**: Tagalog (native TTS) + Bisaya (Filipino voice fallback)
7. **Phase 2 (Stretch)**: Native Bisaya TTS via fine-tuning

---

## 🏆 Hackathon Fit

### Primary Track: **Impact Track - Digital Equity & Inclusivity** ($10k)
✅ Breaks down language barriers  
✅ Intuitive interfaces  
✅ Closes AI skills gap  
✅ Serves underserved communities  

### Secondary Track: **Impact Track - Global Resilience** ($10k)
✅ Disaster response and emergency communications  
✅ Anticipates and responds to pressing challenges  
✅ Climate-related emergency communications  

### Main Track Potential: **$50k+**
Strong contender due to:
- Clear, measurable real-world impact
- Compelling story (life-saving technology)
- Technical innovation
- Scalable beyond Philippines

### Special Technology Track:
- **Ollama** ($10k): Gemma 4 served via Ollama inside Modal container ⭐️ CONFIRMED FIT
  - Modal has official support for running Ollama on GPU containers (modal.com/docs/examples/ollama)
  - Clean serverless deployment: scales to zero when not in use

---

## 🔧 Technical Architecture

### Core Components

```
┌─────────────────────────────────────────────────────────────┐
│                    WeatherSpeak PH System                    │
└─────────────────────────────────────────────────────────────┘

1. PDF INGESTION & PARSING
   ├─ Input: PAGASA bulletin folders by storm
   │  ├─ Each folder: multiple sequential bulletins (#01, #02... #FINAL)
   │  └─ Parse individual PDFs or entire storm timeline
   ├─ OCR/Text extraction (pdfplumber, PyPDF2)
   ├─ Structured data extraction per bulletin:
   │  ├─ Bulletin number, timestamp
   │  ├─ Storm name, category, location
   │  ├─ Wind speed, rainfall, affected areas
   │  ├─ Warnings, evacuation notices
   │  └─ Movement/trajectory
   ├─ Output: Structured JSON per bulletin
   └─ Timeline aggregation: all bulletins for storm summary

2. GEMMA 4 PROCESSING (SERVER-SIDE via Modal + Ollama)
   ├─ Model: Gemma 4 26B or 31B (better quality for translation)
   ├─ Deployment: Modal (serverless GPU) running Ollama container
   │  ├─ Modal spins up GPU container on demand, serves Ollama REST API
   │  ├─ Scales to zero when idle (cost-efficient)
   │  └─ Qualifies for Ollama special technology track ($10k)
   ├─ Two Processing Modes:
   │
   │  MODE 1: Direct Translation (Latest Bulletin)
   │  ├─ Input: Single bulletin JSON
   │  ├─ Tasks:
   │  │  ├─ Extract key information
   │  │  ├─ Simplify technical language
   │  │  ├─ Translate to Tagalog
   │  │  └─ Translate to Bisaya
   │  └─ Output: Translated bulletin text
   │
   │  MODE 2: Storm Summary (All Bulletins) - STRETCH GOAL
   │  ├─ Input: Array of all bulletins for storm
   │  ├─ Tasks:
   │  │  ├─ Analyze storm progression over time
   │  │  ├─ Identify key moments (formation, intensification, landfall)
   │  │  ├─ Synthesize coherent narrative
   │  │  ├─ Translate narrative to Tagalog
   │  │  └─ Translate narrative to Bisaya
   │  └─ Output: Comprehensive storm story
   │
   ├─ Fine-tuning considerations:
   │  ├─ Filipino language pairs
   │  ├─ Weather/disaster terminology
   │  └─ Emergency communication tone
   └─ Function calling: Structured output generation

3. TEXT-TO-SPEECH GENERATION (SERVER-SIDE)
   ├─ Phase 1 TTS Strategy:
   │  ├─ Tagalog: Google Cloud TTS (fil-PH) - native voices
   │  └─ Bisaya: Filipino TTS reading Bisaya text (acceptable fallback)
   ├─ Phase 2 TTS (Stretch Goal):
   │  ├─ Fine-tune Coqui XTTS-v2 for native Bisaya
   │  ├─ Dataset: Bisaya audio (radio, podcasts, Bible recordings)
   │  └─ Training: 5-10 hours audio + transcripts
   ├─ Output format: MP3 audio (optimized for mobile)
   └─ Optional: Simple video with waveform visualization

4. USER INTERFACE (MOBILE-FIRST WEB APP)
   ├─ Location Settings (First-Time Setup)
   │  ├─ User selects their location (province/city)
   │  ├─ Dropdown: All Philippine provinces + major cities
   │  ├─ Save to localStorage for persistence
   │  └─ Optional: GPS/browser geolocation
   ├─ Storm Browser
   │  ├─ List of storms (by year, severity)
   │  ├─ Search/filter functionality
   │  ├─ Show distance from user's location
   │  └─ Storm details page
   ├─ Dialect Selection (Global setting)
   │  ├─ Tagalog
   │  └─ Bisaya/Cebuano
   ├─ Two Audio Modes:
   │  │
   │  │  MODE 1: Latest Bulletin (Personalized)
   │  │  ├─ Display storm overview with context:
   │  │  │  ├─ "120 km east of your location (Cebu City)"
   │  │  │  ├─ "Heading northwest at 25 km/h"
   │  │  │  ├─ "Expected to reach you in 5 hours"
   │  │  │  └─ "4.5M people affected in your region"
   │  │  ├─ Audio player with personalized context
   │  │  ├─ Download button (MP3)
   │  │  └─ Show bulletin metadata (time, number)
   │  │
   │  │  MODE 2: Storm Summary (Regional Impact)
   │  │  ├─ "Generate Storm Story" button
   │  │  ├─ Loading state (AI synthesizing...)
   │  │  ├─ Audio includes:
   │  │  │  ├─ Full storm progression
   │  │  │  ├─ All affected provinces + populations
   │  │  │  ├─ Major cities impacted
   │  │  │  └─ Total casualty/displacement figures
   │  │  ├─ Visual timeline of bulletins
   │  │  ├─ Interactive map showing storm track
   │  │  └─ Download full summary
   │
   ├─ Progressive Web App (PWA) for app-like experience
   ├─ Offline playback (HTML5 audio, service workers)
   └─ Download management (see what's cached)

5. DEPLOYMENT STRATEGY
   ├─ Backend: 
   │  ├─ Gemma 4 via Ollama on Modal (serverless GPU container)
   │  ├─ Google Cloud TTS API
   │  └─ PostgreSQL/Supabase for bulletin storage
   ├─ Frontend: Mobile-first PWA (Vercel deployment)
   └─ Distribution: Community radio stations, local govt units
```

### Why Gemma 4?

✅ **Open models** - Can self-host for data sovereignty  
✅ **Multimodal understanding** - PAGASA bulletins contain storm track maps; Gemma 4 vision can interpret these map images to extract trajectory, landfall zone, and storm position — complementing the text extraction  
✅ **Function calling** - Structured output for translations  
✅ **Powerful models** - 26B/31B for high-quality translation  
✅ **Cost-effective** - Run on Modal (serverless GPU) via Ollama  

---

## 📊 Evaluation Scoring Strategy

| Criterion | Points | Our Strategy |
|-----------|--------|--------------|
| **Impact & Vision** | 40 | ⭐️ **STRONGEST AREA** - Life-saving, addresses real disaster response needs, serves 110M+ Filipinos, 74+ languages |
| **Video & Storytelling** | 30 | Show real PAGASA bulletin → transformation → audio in multiple dialects. Interview Filipino communities. Demo during actual weather event if timing works. |
| **Technical Execution** | 30 | Functional demo with real PDFs, multiple dialects, audio generation. Clean code, well-documented. Show Gemma 4 capabilities. |

### Video Strategy (3 minutes)
**Structure:**
- **0:00-0:30** - The Problem: Show PAGASA English bulletin, Filipino communities struggling with language barrier
- **0:30-1:00** - The Crisis: Statistics on typhoon impacts, communication failures
- **1:00-1:45** - The Solution: Demo WeatherSpeak PH - upload PDF → instant audio in Bisaya, Tagalog, Kapampangan
- **1:45-2:30** - The Impact: Show technology in use, testimonials (or simulated community radio use)
- **2:30-3:00** - The Vision: Scale to other countries, other emergency information, call to action

**Emotional hooks:**
- Real typhoon footage
- Stories of communication barriers
- Elderly grandmother hearing weather report in her native language for first time
- Community radio host using the tool

---

## 🚀 Implementation Roadmap

### **PHASE 1: Core System (Week 1-3)**

#### Week 1: Foundation & Parsing (Apr 9-15)
- [ ] Clone bulletin-archive repo
- [ ] Analyze PDF structure (sample 10-20 bulletins from different storms)
- [ ] Build PDF parser (extract: storm name, category, wind speed, warnings, affected areas)
- [ ] Set up Gemma 4 environment (Ollama locally or API)
- [ ] Test: PDF → structured JSON extraction

#### Week 2: Translation & TTS Integration (Apr 16-22)
- [ ] **Mode 1: Direct Translation**
  - [ ] Prompt engineer Gemma 4 for English → Tagalog (single bulletin)
  - [ ] Prompt engineer Gemma 4 for English → Bisaya (single bulletin)
  - [ ] Test with 5 sample FINAL bulletins from different storms
- [ ] **Set up Google Cloud TTS**
  - [ ] Create GCP account, enable TTS API
  - [ ] Test fil-PH voices (Standard, WaveNet, Neural2)
  - [ ] Test: Tagalog text → native Filipino audio
  - [ ] Test: Bisaya text → Filipino TTS (fallback approach)
- [ ] **Validate translations**
  - [ ] Recruit Tagalog speakers (r/Philippines, Discord)
  - [ ] Recruit Bisaya speakers (r/Cebu, r/Visayas)
  - [ ] Get feedback on naturalness, accuracy, terminology
- [ ] **Build backend API**
  - [ ] FastAPI or Next.js API routes
  - [ ] POST /translate-bulletin (single bulletin)
  - [ ] GET /storm/{id}/bulletins (list all bulletins)
  - [ ] Set up Supabase/PostgreSQL schema
- [ ] **Mode 2 Prototype (If time permits)**
  - [ ] Experiment: feed Gemma 4 multiple bulletins
  - [ ] Prompt engineering for narrative synthesis
  - [ ] Test if summary quality justifies complexity

#### Week 3: Frontend & Integration (Apr 23-29)
- [ ] **Build mobile-first PWA (React/Next.js)**
  - [ ] Project setup with TypeScript
  - [ ] Global dialect selector (Tagalog/Bisaya)
  - [ ] Storm browser UI (grid/list view)
  - [ ] Search and filter storms
- [ ] **Mode 1: Latest Bulletin UI**
  - [ ] Storm detail page
  - [ ] Display parsed bulletin info (wind speed, warnings, etc.)
  - [ ] Audio player component (play/pause, progress bar)
  - [ ] Download button (save MP3)
  - [ ] Loading states, error handling
- [ ] **Mode 2: Storm Summary UI (Stretch Goal)**
  - [ ] "Generate Storm Story" button
  - [ ] Loading animation (AI processing multiple bulletins)
  - [ ] Display narrative text + audio player
  - [ ] Visual timeline showing all bulletins
  - [ ] Download summary audio
- [ ] **PWA offline functionality**
  - [ ] Service worker setup
  - [ ] Cache audio files for offline playback
  - [ ] Show cached content in UI
  - [ ] Background sync for new bulletins
- [ ] **End-to-end testing**
  - [ ] PDF → Gemma 4 → TTS → downloadable audio
  - [ ] Test on mobile devices (iOS Safari, Android Chrome)
  - [ ] Audio file size optimization (64-128 kbps MP3)
- [ ] **Deploy to Vercel**
  - [ ] Connect GitHub repo
  - [ ] Set up environment variables
  - [ ] Test production deployment

### **PHASE 2: Bisaya TTS Experiment (Week 3-4, Parallel Track)**

#### Week 3-4: Native Bisaya TTS (Stretch Goal)
- [ ] Research Bisaya audio datasets
  - [ ] Check Filipino Bible audio (YouVersion, Faith Comes By Hearing)
  - [ ] Search for Bisaya radio/podcast archives
  - [ ] Contact Filipino communities for recordings
- [ ] Set up Coqui XTTS-v2 development environment
- [ ] Prepare training data (audio + transcripts)
- [ ] Fine-tune model (requires GPU: Colab Pro or Lambda Labs)
- [ ] Test quality vs. Filipino-TTS-reading-Bisaya fallback
- [ ] If successful: integrate into production
- [ ] If not ready: document as "in progress" for video

### Week 4: Demo & Video (Apr 30-May 6)
- [ ] Record demo with multiple real bulletins
- [ ] Film video segments (problem, solution, impact)
- [ ] Get community testimonials or feedback
- [ ] Edit video (aim for professional quality)
- [ ] Prepare live demo deployment

### Week 5: Submission (May 7-18)
- [ ] Write Kaggle writeup (≤1,500 words)
- [ ] Final code cleanup & documentation
- [ ] Deploy live demo (GitHub Pages + backend)
- [ ] Upload video to YouTube
- [ ] Submit on Kaggle (deadline: May 18)

---

## 📚 Data Sources

### Bulletin Archive
- **Repo**: https://github.com/pagasa-parser/bulletin-archive
- **Format**: PDFs organized by storm
- **Naming**: `PAGASA_YY_TCXX_StormName_[SWB|TCB|TCA]#NN.pdf`
- **Copyright**: Public domain (Philippine government work)
- **Coverage**: Late 2020 to present

### Sample Bulletins to Test With
- Recent typhoons: 2024-2026 bulletins
- Various bulletin types: SWB, TCB, TCA
- Different severity levels
- Final vs. intermediate bulletins

---

## 🎨 Dialect Implementation Strategy

### **Phase 1 - Hackathon Core (Week 1-3)**
Focus on **2 dialects** to prove concept:

1. **Tagalog/Filipino** (~28M speakers)
   - ✅ Native TTS available (Google Cloud: `fil-PH`)
   - ✅ Multiple high-quality voices (Standard, WaveNet, Neural2)
   - ✅ Perfect pronunciation guaranteed

2. **Cebuano/Bisaya** (~27M speakers)  
   - 🔶 **Fallback**: Filipino TTS reading Bisaya text
   - 🔶 Intelligible due to linguistic similarity
   - 🔶 Acknowledge as "v1" in demo, show roadmap

### **Phase 2 - Stretch Goal (Week 3-4)**
If time permits:

3. **Native Bisaya TTS** (experimental)
   - Tool: Coqui XTTS-v2 fine-tuning
   - Dataset: 5-10 hours Bisaya audio + transcripts
   - Sources: Radio archives, Bible recordings, podcasts


### **Post-Hackathon Roadmap**
4. **Ilocano** (~10M speakers)
5. **Hiligaynon** (~9M speakers)  
6. **Waray** (~4M speakers)
7. Other regional languages

---

## 🔍 Technical Challenges & Solutions

| Challenge | Solution |
|-----------|----------|
| PDF parsing accuracy | Use multiple parsers (PyPDF2, pdfplumber), validate with regex patterns |
| Limited Filipino training data for Gemma 4 | Use few-shot prompting with examples, synthetic data generation |
| Dialect-specific weather terminology | Build glossaries with meteorological terms, validate with native speakers |
| No native Bisaya TTS available | **Phase 1**: Use Filipino TTS reading Bisaya (acceptable). **Phase 2**: Fine-tune Coqui XTTS |
| Bisaya TTS training data scarcity | Source from Bible recordings, radio archives, podcast transcripts, community contributions |
| Audio file size for mobile download | MP3 compression (64-128 kbps), streaming option for good connectivity |
| Translation quality validation | Recruit Filipino speakers on social media, Reddit r/Philippines, Discord communities |
| Server costs for TTS generation | Google Cloud TTS free tier (1M chars/month), cache generated audio, Ollama self-hosting for Gemma |
| Geographic data compilation | One-time: Build `philippines-geography.json` from PSA census + Wikipedia coordinates (3-4 hours) |
| Personalizing audio at scale | Cache base translations, generate personalized snippets on-demand, pre-generate for major cities |
| Coordinate extraction from PDFs | Bulletins include lat/lon in text - regex pattern matching, validate format |

---

## 💪 Competitive Advantages

1. **Real, immediate need** - Not a hypothetical problem, 110M people affected, ~20 typhoons/year
2. **Government data available** - Public domain PAGASA archive, ready to use
3. **Measurable impact** - Lives saved, 55M+ dialect speakers served (Tagalog + Bisaya)
4. **Scalable** - Transfer to other languages, countries, disaster types (Indonesia, Vietnam, India)
5. **Emotional story** - Natural disasters, family safety, grandmother hearing warnings in her language
6. **Technical innovation** - Multi-dialect translation + AI synthesis + optional TTS fine-tuning (Bisaya)
7. **Personalized context** - Not just translation, but "how far from YOU, how many people affected"
8. **Community validation** - Can get real feedback from 2.6M Filipino Reddit/Discord users
9. **Practical architecture** - Works with fallback TTS, perfect for iterative improvement
10. **Potential dual prize winner** - Digital Equity ($10k) + Ollama track ($10k)
11. **Open source contribution** - First Bisaya TTS model + Philippine geography dataset released to community
12. **Beyond translation** - Geographic context shows deep understanding of user needs

---

## 📝 Writeup Outline (1,500 words max)

1. **Introduction** (150 words)
   - Problem statement
   - Why this matters now

2. **Technical Architecture** (500 words)
   - PDF parsing pipeline
   - Gemma 4 integration (specific model, prompts, fine-tuning)
   - Translation approach
   - TTS/video generation
   - Edge deployment strategy

3. **Implementation & Challenges** (400 words)
   - Key technical hurdles overcome
   - Dialect validation process
   - Performance optimization
   - Offline capabilities

4. **Results & Impact** (300 words)
   - Demo statistics (bulletins processed, languages supported)
   - User feedback/testing
   - Potential reach (population served)

5. **Future Work** (150 words)
   - Scale to more dialects
   - SMS/WhatsApp integration
   - Other emergency information types
   - Regional partnerships

---

## 🎬 Next Steps

1. **Clone bulletin archive** and analyze ~10 sample PDFs
2. **Set up Gemma 4** locally (Ollama or llama.cpp)
3. **Build PDF parser** for structured extraction
4. **Test translation** with Gemma 4 (Tagalog first, then Bisaya)
5. **Find TTS solution** for Filipino languages
6. **Create proof-of-concept demo** (one bulletin, two languages)

---

## 💬 Decisions Made & To-Do

### ✅ Decided:
- **Dialects**: Tagalog + Bisaya (focus on 2 for hackathon)
- **TTS Strategy**: Google Cloud TTS for Tagalog, Filipino voice reading Bisaya (Phase 1 fallback)
- **Stretch Goal**: Fine-tune Coqui XTTS-v2 for native Bisaya (Phase 2)
- **No Pipecat**: Not suitable for batch audio generation use case
- **Deployment**: Vercel (frontend), Supabase/PostgreSQL (database)
- **Phased Approach**: Core system first, TTS experiment in parallel
- **Dual-Mode System**: 
  - ✅ **Mode 1**: Latest bulletin translation (MVP core)
  - ✅ **Mode 2**: Storm summary synthesis (stretch goal for impact)
- **Bulletin Strategy**: Use multiple PDFs per storm for Mode 2 narrative generation
- **Geographic Context**: 
  - ✅ **Add Phase 1.5**: User location, distance calculations, population impact
  - ✅ Personalized audio ("120km from your location")
  - ✅ Static Philippine geography dataset

### 📝 To Prepare (Week 2):
- [ ] Compile `philippines-geography.json` with all 81 provinces + major cities
  - [ ] PSA 2020 Census data (population)
  - [ ] Province/city coordinates (OpenStreetMap/Wikipedia)
  - [ ] Major cities per province
- [ ] Create location selector UI component (dropdown)
- [ ] Implement haversine distance calculation function
- [ ] Write Gemma 4 prompts with geographic context placeholders

### ❓ To Investigate:
- [ ] Which Gemma 4 model? (26B vs 31B - quality vs. inference speed)
- [ ] Gemma 4 deployment: Ollama locally vs. API (cost/speed tradeoff)
- [ ] Fine-tune Gemma 4 or just prompt engineering? (depends on translation quality)
- [ ] Video style: Live action + screen recording + Filipino community testimonials?
- [ ] Recruit Filipino testers: r/Philippines, Filipino Discord servers, LinkedIn
- [ ] Bisaya audio sources: Bible recordings (YouVersion), GMA/ABS-CBN radio archives
- [ ] Target **Ollama** prize ($10k) — Gemma 4 served via Ollama on Modal

---

## 🏅 Success Metrics

**For Hackathon:**
- ✅ Functional demo with real PAGASA PDFs (10+ sample bulletins from 5+ storms)
- ✅ 2 Filipino dialects: Tagalog (native TTS) + Bisaya (fallback or native if Phase 2 succeeds)
- ✅ **Mode 1**: Latest bulletin translation & audio generation (core MVP)
- ✅ **Mode 2**: Storm summary synthesis (demonstrates Gemma 4 intelligence)
- ✅ Audio generation and download working (MP3 format, optimized for mobile)
- ✅ Mobile PWA with offline playback capability
- ✅ Compelling 3-minute video showcasing both modes
- ✅ Clean, documented code repo (GitHub with README)
- ✅ Strong writeup with technical depth (≤1,500 words)
- 🎯 **Bonus 1**: Native Bisaya TTS (first in the world!) if Phase 2 completes
- 🎯 **Bonus 2**: Visual timeline UI for storm progression

**For Real-World Impact:**
- Community feedback/validation
- Accuracy of translations (verified by native speakers)
- Partnerships with local radio stations
- PAGASA interest/adoption
- International adaptation (Indonesia, Vietnam, India, etc.)

---
## 🗺️ **Geographic Context Enhancement (Phase 1.5)**

### **Why This Matters**

**Without context:**
> "Typhoon Odette at 11.5°N, 125.3°E, Signal #4 in Eastern Samar"

**With geographic context:**
> "Typhoon Odette is 120 kilometers east of Cebu City, moving toward you at 25 km/h. 
> Expected to reach your area in 5 hours. Signal #4 affects Eastern Samar where 
> 467,000 people live. Your province (Cebu) with 5.1 million people is next."

### **Features to Implement**

#### **1. User Location Selection**

**UI Flow:**
```
On first visit:
┌─────────────────────────────────────┐
│  📍 Where are you located?          │
│                                     │
│  Province: [Cebu ▼]                │
│  City:     [Cebu City ▼]           │
│                                     │
│  Or use current location [📍 GPS]  │
│                                     │
│      [Continue]                     │
└─────────────────────────────────────┘

Saved to localStorage, editable in settings
```

**Implementation:**
- Dropdown with all 81 provinces + major cities
- Optional: Browser geolocation API (if user allows)
- Store in localStorage for persistence
- Display in header: "📍 Your location: Cebu City"

#### **2. Distance to Storm**

**Calculation:**
```python
from math import radians, sin, cos, sqrt, atan2

def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two points in km"""
    R = 6371  # Earth's radius in km
    
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    
    return R * c

# Extract from bulletin
storm_lat, storm_lon = extract_coordinates(bulletin_pdf)

# Get user's city coordinates (from static data)
user_coords = CITY_COORDINATES[user_city]

distance = haversine_distance(
    storm_lat, storm_lon,
    user_coords['lat'], user_coords['lon']
)
```

**Display:**
- "120 km east of Cebu City"
- "Moving toward you" or "Moving away"
- "Expected to reach in 5 hours" (if heading toward user)

#### **3. Affected Population**

**From Bulletin:**
- Parse: "Signal #4: Eastern Samar, Southern Leyte"
- Parse: "Signal #3: Cebu, Bohol"

**Lookup Population:**
```python
PROVINCE_DATA = {
    "Eastern Samar": {
        "population": 467000,
        "region": "Region VIII",
        "capital": "Borongan"
    },
    "Cebu": {
        "population": 5155000,
        "region": "Region VII",
        "capital": "Cebu City"
    }
}

affected_provinces = parse_signal_areas(bulletin)
total_affected = sum(
    PROVINCE_DATA[p]['population'] 
    for p in affected_provinces
)

# Output: "10.2 million people affected"
```

#### **4. Enhanced Gemma 4 Context**

**Input to Gemma 4 (Mode 1):**
```json
{
  "bulletin_text": "...",
  "storm_coordinates": {"lat": 11.5, "lon": 125.3},
  "user_location": {
    "city": "Cebu City",
    "province": "Cebu",
    "coordinates": {"lat": 10.3, "lon": 123.9}
  },
  "distance_to_user": 120,
  "direction": "east",
  "affected_provinces": [
    {"name": "Eastern Samar", "population": 467000, "signal": 4},
    {"name": "Cebu", "population": 5155000, "signal": 3}
  ]
}
```

**Enhanced Prompt:**
```
You are translating a weather bulletin for someone in {user_city}.

Context:
- The storm is {distance}km {direction} of their location
- It's moving {toward/away} at {speed}km/h
- {total_population:,} people affected in {num_provinces} provinces

Translate to {dialect} and include:
1. Personal relevance: how far the storm is from them
2. Timeline: when it might reach their area
3. Scale: how many people affected
4. Action: what they should do based on their signal level
```

### **Required Static Data**

#### **Create: `data/philippines-geography.json`**

```json
{
  "provinces": {
    "Cebu": {
      "population": 5155000,
      "region": "Region VII - Central Visayas",
      "capital": "Cebu City",
      "major_cities": ["Cebu City", "Mandaue", "Lapu-Lapu"],
      "coordinates": {"lat": 10.3157, "lon": 123.8854}
    },
    "Eastern Samar": {
      "population": 467000,
      "region": "Region VIII - Eastern Visayas",
      "capital": "Borongan",
      "major_cities": ["Borongan", "Guiuan"],
      "coordinates": {"lat": 11.6, "lon": 125.4}
    }
    // ... all 81 provinces
  },
  
  "cities": {
    "Cebu City": {
      "province": "Cebu",
      "population": 964169,
      "coordinates": {"lat": 10.3157, "lon": 123.8854}
    },
    "Manila": {
      "province": "Metro Manila",
      "population": 1846513,
      "coordinates": {"lat": 14.5995, "lon": 120.9842}
    }
    // ... top 50 cities
  }
}
```

**Data Sources:**
1. **Philippine Statistics Authority (PSA)**: https://psa.gov.ph/
   - 2020 Census population data
   - Province/city classifications

2. **Wikipedia**: 
   - "List of provinces in the Philippines"
   - Coordinates for each province capital

3. **OpenStreetMap Nominatim**:
   - Get exact coordinates for cities
   - `https://nominatim.openstreetmap.org/search?q=Cebu+City,Philippines`

**Time to compile:** 3-4 hours one-time

### **Implementation Timeline**

**Week 2 (Apr 16-22):**
- [ ] Compile `philippines-geography.json` (3-4 hours)
- [ ] Add location selector UI component
- [ ] Implement haversine distance calculation
- [ ] Test with sample bulletins

**Week 3 (Apr 23-29):**
- [ ] Integrate geographic context into Gemma 4 prompts
- [ ] Update Mode 1 audio generation with personalized info
- [ ] Update Mode 2 to include population statistics
- [ ] Add distance display in storm browser
- [ ] Test: Does audio sound natural with extra context?

### **Audio Enhancement Examples**

#### **Mode 1 (Latest Bulletin) - Tagalog:**

**Before:**
> "Ang Bagyong Odette ay Category 4 na may hangin na 195 km/h. 
> Itinataas ang Signal #4 sa Eastern Samar."

**After (with geographic context):**
> "Ang Bagyong Odette ay Category 4 na may hangin na 195 km/h. 
> Ito ay nasa 120 kilometro silangan ng Cebu City kung saan kayo nakatira. 
> Papalapit ito nang 25 km/h at aabot sa inyong lugar sa loob ng 5 oras.
> Itinataas ang Signal #4 sa Eastern Samar na may 467,000 na tao. 
> Ang Cebu, na may 5.1 milyong tao, ay nasa Signal #3. 
> Maghanda na at makinig sa local authorities."

#### **Mode 2 (Storm Summary) - Bisaya:**

**Before:**
> "Ang Bagyo Odette mitungha sa Disyembre 12 ug milapad sa super typhoon. 
> Mihampak kini sa Siargao Island sa Disyembre 16."

**After (with geographic context):**
> "Ang Bagyo Odette mitungha sa Disyembre 12, 500 km layo sa Mindanao. 
> Sa loob sa tulo ka adlaw, milapad kini sa super typhoon nga adunay 
> 195 km/h nga hangin.
> 
> Sa Disyembre 16, mihampak kini sa Siargao Island diin 179,000 ka tawo namuyo. 
> Human niana, milihok kini paingon sa Southern Leyte (421,000 ka tawo) 
> ug Cebu (5.1 milyon). 
> 
> Sa tibuok, sobra sa 10 milyon ka Pilipino ang naapektuhan sa 9 ka probinsya."

### **Benefits for Judges**

✅ **Personal relevance** - Not just academic translation  
✅ **Actionable information** - Users know if they're in danger  
✅ **Scale comprehension** - "10M affected" hits harder than province names  
✅ **Technical sophistication** - Shows data integration skills  
✅ **Real-world thinking** - Anticipated user needs beyond base requirements  

---
## �️ Implementation Details: Dual-Mode System

### **Mode 1: Latest Bulletin Translation (Core MVP)**

**Purpose:** Translate the most recent bulletin for immediate awareness

**Data Flow:**
```
PAGASA PDF (latest) 
  → Parse text
  → Gemma 4: Extract + Simplify + Translate
  → Google Cloud TTS
  → MP3 audio (Tagalog + Bisaya)
```

**Gemma 4 Prompt Example:**
```
You are a weather translator for Filipino communities. 

Input: PAGASA Severe Weather Bulletin in English
Task: 
1. Extract key information (storm name, location, wind speed, warnings)
2. Simplify technical language for general public
3. Translate to [TAGALOG/BISAYA] maintaining urgent tone

Example English Input:
"Severe Weather Bulletin #15. Typhoon ODETTE (RAI) has intensified into a 
super typhoon with maximum sustained winds of 195 km/h near the center. 
Signal #4 is raised over Eastern Samar and Southern Leyte..."

Expected Output (Tagalog):
"Babala sa Matinding Panahon #15. Ang Bagyong ODETTE ay lumakas na at 
naging super typhoon na may hangin na 195 km/h. Itinataas ang Signal #4 
sa Eastern Samar at Southern Leyte..."
```

**Processing Time:** ~2-5 seconds per bulletin

---

### **Mode 2: Storm Summary Synthesis (Stretch Goal)**

**Purpose:** Create a comprehensive narrative of the entire storm lifecycle

**Data Flow:**
```
All bulletins for storm (#01 → #FINAL)
  → Parse all PDFs
  → Gemma 4: Analyze timeline + Synthesize story
  → Translate narrative
  → Google Cloud TTS
  → MP3 audio (comprehensive story)
```

**Gemma 4 Prompt Example:**
```
You are a disaster documentarian creating educational storm summaries.

Input: Array of 15 bulletins tracking Typhoon ODETTE from Dec 12-18, 2024
Task:
1. Analyze the storm's progression over time
2. Identify key moments:
   - Initial formation and classification
   - Intensification to super typhoon status
   - Landfall locations and times
   - Peak danger period
   - Weakening and conclusion
3. Create a coherent narrative in [TAGALOG/BISAYA] that:
   - Tells the story chronologically
   - Emphasizes life-saving information
   - Suitable for radio broadcast (conversational tone)
   - 2-3 minutes when read aloud

Example Output Structure:
"Noong Disyembre 12, 2024, nabuo ang Bagyo Odette bilang tropical 
depression sa silangan ng Mindanao. Sa loob lamang ng tatlong araw, 
lumakas ito at naging super typhoon na may hangin na 195 km/h..."
```

**Processing Time:** ~10-30 seconds (analyzing multiple bulletins)

**Benefits for Hackathon:**
- ✅ Shows off Gemma 4's advanced synthesis capabilities
- ✅ Goes beyond simple translation → AI intelligence
- ✅ Better demo/video storyline
- ✅ Judges see innovation beyond API calls

---

## 📊 Database Schema (Supabase/PostgreSQL)

```sql
-- Storms table
CREATE TABLE storms (
  id UUID PRIMARY KEY,
  name TEXT NOT NULL,
  year INTEGER NOT NULL,
  max_category INTEGER,
  total_bulletins INTEGER,
  first_bulletin_date TIMESTAMP,
  last_bulletin_date TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Bulletins table
CREATE TABLE bulletins (
  id UUID PRIMARY KEY,
  storm_id UUID REFERENCES storms(id),
  bulletin_number INTEGER NOT NULL,
  is_final BOOLEAN DEFAULT FALSE,
  pdf_url TEXT NOT NULL,
  raw_text TEXT,
  parsed_data JSONB,  -- structured storm data
  issued_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Translations table (Mode 1: individual bulletins)
CREATE TABLE bulletin_translations (
  id UUID PRIMARY KEY,
  bulletin_id UUID REFERENCES bulletins(id),
  dialect TEXT NOT NULL,  -- 'tagalog' or 'bisaya'
  translated_text TEXT NOT NULL,
  audio_url TEXT,
  audio_duration_seconds INTEGER,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Storm summaries table (Mode 2: full storm narrative)
CREATE TABLE storm_summaries (
  id UUID PRIMARY KEY,
  storm_id UUID REFERENCES storms(id),
  dialect TEXT NOT NULL,
  narrative_text TEXT NOT NULL,
  audio_url TEXT,
  audio_duration_seconds INTEGER,
  bulletins_analyzed INTEGER,  -- how many bulletins went into this
  created_at TIMESTAMP DEFAULT NOW()
);

-- User locations table (for personalized context)
CREATE TABLE user_locations (
  id UUID PRIMARY KEY,
  session_id TEXT NOT NULL,  -- or user_id if auth implemented
  province TEXT NOT NULL,
  city TEXT,
  coordinates JSONB,  -- {"lat": 10.3, "lon": 123.9}
  last_updated TIMESTAMP DEFAULT NOW()
);

-- Cache for geographic enrichment
CREATE TABLE geographic_context_cache (
  bulletin_id UUID PRIMARY KEY REFERENCES bulletins(id),
  affected_provinces JSONB,  -- [{"name": "Cebu", "population": 5155000, "signal": 3}]
  total_affected_population INTEGER,
  storm_coordinates JSONB,  -- {"lat": 11.5, "lon": 125.3}
  created_at TIMESTAMP DEFAULT NOW()
);
```

---

## 🎥 Video Demo Script (3 minutes)

**Using Both Modes for Maximum Impact**

**0:00-0:30 - The Problem**
- Show 15 English PDF bulletins scattered on screen
- "During Typhoon Odette, PAGASA released 15 bulletins over 6 days"
- "All in English. But 27 million Filipinos speak Bisaya..."

**0:30-1:00 - Mode 1: Instant Translation**
- Upload latest bulletin
- Show Gemma 4 processing (loading animation)
- Audio plays in Bisaya: "Babala sa Makusog nga Bagyo..."
- "Each bulletin, instantly accessible in your dialect"

**1:00-1:45 - Mode 2: AI Synthesis**
- Click "Generate Storm Story" button
- Show all 15 bulletins feeding into Gemma 4
- Loading: "Analyzing storm progression..."
- Play comprehensive 2-minute narrative
- "But we go further - our AI creates the complete story"

**1:45-2:15 - The Impact**
- B-roll: Filipino families, community radio
- "55 million Filipinos speak languages other than English"
- "Life-saving information should reach everyone"

**2:15-2:45 - Technical Excellence**
- Quick architecture diagram
- "Powered by Gemma 4's 26B parameter model"
- "Optional: First-ever Bisaya TTS (if Phase 2 succeeds)"
- Show on mobile device (PWA, offline playback)

**2:45-3:00 - Call to Action**
- "WeatherSpeak PH: Because safety shouldn't have a language barrier"
- GitHub repo, demo link
- "Open source - scalable to any language, any country"

---

## 🏆 Competitive Advantages of Dual-Mode Approach

### **Mode 1 Advantages:**
✅ Simple, reliable, fast (MVP proof)  
✅ Addresses immediate need (latest info)  
✅ Scalable (automated for new bulletins)  

### **Mode 2 Advantages:**
✅ **Differentiator** - no competitor will have this  
✅ Shows advanced AI capabilities (synthesis > translation)  
✅ Educational value (understand full storm context)  
✅ Stronger technical story for judges  
✅ Potential media interest ("AI creates storm documentaries")  

### **Combined Impact:**
🎯 **Impact & Vision**: Life-saving + educational  
🎯 **Technical Depth**: Translation + AI synthesis + TTS  
🎯 **Video Pitch**: Two features = more compelling demo  

---

**Last Updated**: April 9, 2026  
**Deadline**: May 18, 2026 (39 days remaining)

### Why This Could Be Groundbreaking

Building the **first native Bisaya TTS** would be:
- ✅ World's first for 27M speakers
- ✅ Major technical achievement for hackathon

- ✅ Publishable open-source contribution
- ✅ Potential academic paper/blog post

### Implementation Path

**Tool:** Coqui XTTS-v2 (Zero-shot multilingual TTS)
- Based on XTTS architecture
- Supports voice cloning with minimal data
- Can fine-tune for new languages

**Minimum Requirements:**
- 5-10 hours of Bisaya audio
- Paired text transcripts
- GPU access (Colab Pro: $10/mo, or Lambda Labs)

**Potential Data Sources:**

1. **Religious Recordings** (highest quality, readily available)
   - Bisaya Bible audio (YouVersion app, Faith Comes By Hearing)
   - Church sermons/homilies
   - Religious podcasts

2. **Radio/Broadcast Archives**
   - DZMB Cebu City stations
   - GMA Network Visayas broadcasts
   - Community radio recordings

3. **Open Datasets**
   - Common Voice (Mozilla) - limited Bisaya
   - LibriVox (public domain audiobooks)
   - Filipino podcast archives

4. **Community Sourcing**
   - Recruit Bisaya speakers to record weather bulletins
   - Offer co-authorship on open-source release
   - Post on r/Cebu, r/Philippines

### Training Process

```bash
# 1. Install Coqui TTS
pip install TTS

# 2. Prepare dataset
# Format: /data/bisaya/audio/*.wav + /data/bisaya/transcripts/*.txt

# 3. Fine-tune XTTS-v2
tts-server --model_name tts_models/multilingual/multi-dataset/xtts_v2 \
           --fine_tune \
           --dataset_path ./data/bisaya

# 4. Test quality
tts --text "Ang bagyo nag-anhi sa Mindanao" \
    --model_path ./bisaya_tts_model \
    --out_path test_output.wav
```

**Time Estimate:**
- Data collection: 1 week
- Data preparation (transcription/cleaning): 3-5 days
- Training: 1-2 days with GPU
- Testing/iteration: 2-3 days

**Success Criteria:**
- Bisaya speakers rate audio 7+/10 for intelligibility
- Better than Filipino-voice-reading-Bisaya baseline
- Demonstrates potential for production use

---

**Last Updated**: April 9, 2026  
**Deadline**: May 18, 2026 (39 days remaining)
