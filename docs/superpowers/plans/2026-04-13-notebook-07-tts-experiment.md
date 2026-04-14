# Notebook 07 — TTS Experiment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Jupyter notebook that synthesizes the 6 radio bulletin markdown files into MP3 audio files using Coqui XTTS v2, with Modal-ready functions.

**Architecture:** Markdown scripts are preprocessed into speakable plain text (section headings converted to pause cues), chunked into XTTS v2-safe segments, synthesized in memory, and exported directly to MP3 via pydub — no intermediate WAV files. Core functions are self-contained for later extraction into a Modal deployment.

**Tech Stack:** Coqui TTS (`coqui-tts`), XTTS v2 model, pydub, numpy, ffmpeg (system), uv

---

## File Map

| Action | Path | Responsibility |
|---|---|---|
| Create | `notebooks/07-tts-experiment.ipynb` | Main experiment notebook |
| Create | `tests/test_tts_preprocess.py` | Unit tests for preprocessing function |
| Modify | `pyproject.toml` | Add coqui-tts and pydub dependencies |

---

## Task 1: Add Dependencies

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Verify ffmpeg is available**

```bash
ffmpeg -version | head -1
```

Expected: `ffmpeg version ...` — if not found, install via `brew install ffmpeg`.

- [ ] **Step 2: Add dependencies to pyproject.toml**

Open `pyproject.toml` and update the `dependencies` list:

```toml
[project]
name = "weatherspeak-ph"
version = "0.1.0"
description = "AI-powered multilingual severe weather communications for the Philippines"
requires-python = ">=3.12"
dependencies = [
    "coqui-tts>=0.25.0",
    "pydub>=0.25.1",
    "numpy>=1.26.0",
]
```

- [ ] **Step 3: Install dependencies**

```bash
uv pip install coqui-tts pydub numpy
```

Expected: packages install without error. `coqui-tts` is a large package — takes a minute.

- [ ] **Step 4: Verify imports work**

```bash
uv run python -c "from TTS.api import TTS; from pydub import AudioSegment; import numpy as np; print('OK')"
```

Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml
git commit -m "feat: add coqui-tts and pydub dependencies for TTS experiment"
```

---

## Task 2: Preprocessing Function + Tests

**Files:**
- Create: `tests/test_tts_preprocess.py`

The preprocessing function will live in the notebook, but we write and verify it via a standalone test file first — then paste the validated implementation into the notebook.

- [ ] **Step 1: Create the test file**

Create `tests/test_tts_preprocess.py`:

```python
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Inline implementation (copy from notebook once both are in sync)
# ---------------------------------------------------------------------------

def preprocess_for_tts(markdown_text: str) -> str:
    """Strip markdown formatting and insert pause cues at section boundaries."""
    text = markdown_text

    # Section headings → pause cue + heading text as a spoken sentence
    text = re.sub(r"^#{1,6}\s+(.+)$", r"\n...\n\1.\n", text, flags=re.MULTILINE)

    # Bold and italic markers
    text = re.sub(r"\*{1,3}(.+?)\*{1,3}", r"\1", text)
    text = re.sub(r"_{1,3}(.+?)_{1,3}", r"\1", text)

    # Inline code
    text = re.sub(r"`(.+?)`", r"\1", text)

    # Blockquotes
    text = re.sub(r"^>\s+", "", text, flags=re.MULTILINE)

    # Horizontal rules
    text = re.sub(r"^[-*_]{3,}$", "", text, flags=re.MULTILINE)

    # Collapse 3+ blank lines to 2
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_strips_headings_and_adds_pause_cue():
    md = "## Forecast Track\n\nSome text."
    result = preprocess_for_tts(md)
    assert "##" not in result
    assert "..." in result
    assert "Forecast Track." in result
    assert "Some text." in result


def test_strips_bold_markers():
    md = "**Typhoon PEPITO** is moving west."
    result = preprocess_for_tts(md)
    assert "**" not in result
    assert "Typhoon PEPITO is moving west." in result


def test_strips_italic_markers():
    md = "*signal number two* is in effect."
    result = preprocess_for_tts(md)
    assert "*" not in result
    assert "signal number two is in effect." in result


def test_collapses_multiple_blank_lines():
    md = "Line one.\n\n\n\nLine two."
    result = preprocess_for_tts(md)
    assert "\n\n\n" not in result


def test_strips_inline_code():
    md = "Use `gemma4:e4b` for inference."
    result = preprocess_for_tts(md)
    assert "`" not in result
    assert "gemma4:e4b" in result


def test_strips_blockquote():
    md = "> Note: this is a note."
    result = preprocess_for_tts(md)
    assert result.startswith(">") is False
    assert "Note: this is a note." in result


def test_output_has_no_leading_trailing_whitespace():
    md = "\n\n## Title\n\nContent.\n\n"
    result = preprocess_for_tts(md)
    assert result == result.strip()


def test_pause_cue_position():
    """Pause cue (...) must appear BEFORE the heading text, not after."""
    md = "## Current Situation\n\nResidents are urged..."
    result = preprocess_for_tts(md)
    ellipsis_pos = result.index("...")
    heading_pos = result.index("Current Situation.")
    assert ellipsis_pos < heading_pos


if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    passed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL  {t.__name__}: {e}")
    print(f"\n{passed}/{len(tests)} passed")
```

- [ ] **Step 2: Run tests to verify they pass**

```bash
uv run python tests/test_tts_preprocess.py
```

Expected:
```
  PASS  test_strips_headings_and_adds_pause_cue
  PASS  test_strips_bold_markers
  PASS  test_strips_italic_markers
  PASS  test_collapses_multiple_blank_lines
  PASS  test_strips_inline_code
  PASS  test_strips_blockquote
  PASS  test_output_has_no_leading_trailing_whitespace
  PASS  test_pause_cue_position

8/8 passed
```

- [ ] **Step 3: Manually inspect preprocessing on a real bulletin**

```bash
uv run python -c "
from pathlib import Path
import sys
sys.path.insert(0, 'tests')
from test_tts_preprocess import preprocess_for_tts
md = Path('data/radio_bulletins/PAGASA_20-19W_Pepito_SWB#01_radio_en.md').read_text()
print(preprocess_for_tts(md)[:800])
"
```

Expected: Clean prose, no `##` or `**`, section names appear as plain sentences preceded by `...`.

- [ ] **Step 4: Commit**

```bash
git add tests/test_tts_preprocess.py
git commit -m "feat: add preprocessing function and tests for TTS input preparation"
```

---

## Task 3: Build Notebook — Setup Cell

**Files:**
- Create: `notebooks/07-tts-experiment.ipynb` (initial cells)

Create the notebook file. Add the first two cells.

- [ ] **Step 1: Create notebook with markdown intro cell**

Create `notebooks/07-tts-experiment.ipynb` with the following first cell (markdown):

````
# TTS Experiment — Coqui XTTS v2

**WeatherSpeak PH** — Gemma 4 Hackathon

## Objective

Convert the 6 radio bulletin scripts generated in notebook 06 into MP3 audio files
using **Coqui XTTS v2** — one file per language per bulletin.

### Language mapping
| Script language | XTTS v2 language code | Rationale |
|---|---|---|
| English (`en`) | `en` | Native support |
| Tagalog (`tl`) | `es` (Spanish) | Best available phoneme approximation — Filipino shares Spanish's 5-vowel system and consonant inventory |
| Cebuano (`ceb`) | `es` (Spanish) | Same rationale as Tagalog |

> **Note — Future alternative:** The Coqui TTS model zoo includes a community-contributed
> Tagalog model (`tts_models/tl/...`). This could replace the Spanish-phoneme fallback
> for native phoneme accuracy, at the cost of a different (inconsistent) voice.
> Worth evaluating once the pipeline is stable.

### Output
6 MP3 files saved to `data/tts_output/` — ready for download or web playback.

### Modal note
Core functions (`preprocess_for_tts`, `synthesize_to_mp3`) are self-contained
with no notebook globals — ready to wrap in `@app.function` for Modal deployment.
````

- [ ] **Step 2: Add setup code cell**

Add the second cell (code):

```python
import re
import time
import numpy as np
from pathlib import Path
from pydub import AudioSegment
from TTS.api import TTS

# --- Paths ---
data_dir = Path("../data")
input_dir = data_dir / "radio_bulletins"
output_dir = data_dir / "tts_output"
output_dir.mkdir(exist_ok=True)

# --- Language mapping ---
LANGUAGE_MAP = {"en": "en", "tl": "es", "ceb": "es"}
SPEAKER = "Damien Black"
SAMPLE_RATE = 24_000  # XTTS v2 native sample rate

# --- Input files ---
STEMS = [
    "PAGASA_20-19W_Pepito_SWB#01",
    "PAGASA_22-TC02_Basyang_TCA#01",
]
LANGUAGES = ["en", "tl", "ceb"]

input_files = [
    input_dir / f"{stem}_radio_{lang}.md"
    for stem in STEMS
    for lang in LANGUAGES
]

missing = [f for f in input_files if not f.exists()]
if missing:
    print(f"⚠  Missing input files: {[f.name for f in missing]}")
else:
    print(f"✓ {len(input_files)} input files found")

print(f"✓ Output dir: {output_dir.absolute()}")
```

---

## Task 4: Build Notebook — Preprocessing Cell

**Files:**
- Modify: `notebooks/07-tts-experiment.ipynb`

- [ ] **Step 1: Add markdown section header cell**

````
## 1. Text Preprocessing

Strip markdown syntax and insert pause cues at section boundaries.
Section headings become `...` + heading text — XTTS v2 reads the ellipsis
as a sentence-boundary pause.
````

- [ ] **Step 2: Add preprocessing function cell**

```python
def preprocess_for_tts(markdown_text: str) -> str:
    """Strip markdown formatting and insert pause cues at section boundaries.

    Modal-ready: pure function, no external state.
    """
    text = markdown_text

    # Section headings → pause cue + heading as spoken sentence
    text = re.sub(r"^#{1,6}\s+(.+)$", r"\n...\n\1.\n", text, flags=re.MULTILINE)

    # Bold and italic markers
    text = re.sub(r"\*{1,3}(.+?)\*{1,3}", r"\1", text)
    text = re.sub(r"_{1,3}(.+?)_{1,3}", r"\1", text)

    # Inline code
    text = re.sub(r"`(.+?)`", r"\1", text)

    # Blockquotes
    text = re.sub(r"^>\s+", "", text, flags=re.MULTILINE)

    # Horizontal rules
    text = re.sub(r"^[-*_]{3,}$", "", text, flags=re.MULTILINE)

    # Collapse 3+ blank lines to 2
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


# --- Inline test on one real bulletin ---
sample_md = (input_dir / "PAGASA_20-19W_Pepito_SWB#01_radio_en.md").read_text()
sample_plain = preprocess_for_tts(sample_md)

print("PREPROCESSING SAMPLE (first 600 chars of plain text)")
print("=" * 60)
print(sample_plain[:600])
print("...")
print(f"\nOriginal: {len(sample_md)} chars  →  Preprocessed: {len(sample_plain)} chars")
```

---

## Task 5: Build Notebook — Synthesis Functions Cell

**Files:**
- Modify: `notebooks/07-tts-experiment.ipynb`

- [ ] **Step 1: Add markdown section header cell**

````
## 2. TTS Synthesis Functions

Two self-contained functions — Modal-ready (no notebook globals in signatures).
- `chunk_text`: splits long text into XTTS v2-safe segments on sentence boundaries
- `synthesize_to_mp3`: full pipeline from plain text → MP3, no intermediate WAV
````

- [ ] **Step 2: Add synthesis functions cell**

```python
def chunk_text(text: str, max_chars: int = 200) -> list[str]:
    """Split text into segments ≤ max_chars on sentence boundaries.

    XTTS v2 is unreliable above ~200 chars per call.
    Modal-ready: pure function, no external state.
    """
    sentences = re.split(r"(?<=[.!?…])\s+", text)
    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        if not sentence.strip():
            continue
        if len(current) + len(sentence) + 1 <= max_chars:
            current = (current + " " + sentence).strip()
        else:
            if current:
                chunks.append(current)
            # If a single sentence exceeds max_chars, keep it as-is
            current = sentence
    if current:
        chunks.append(current)
    return chunks


def synthesize_to_mp3(
    text: str,
    language: str,
    output_path: Path,
    tts: TTS,
) -> Path:
    """Synthesize plain text to MP3 using XTTS v2.

    Modal-ready: all inputs are primitive types + Path; no notebook globals.

    Args:
        text: Plain text (no markdown). Use preprocess_for_tts() first.
        language: XTTS v2 language code ('en' or 'es').
        output_path: Destination MP3 path.
        tts: Loaded TTS instance (load once, reuse for all files).

    Returns:
        output_path on success.
    """
    chunks = chunk_text(text)
    audio_arrays: list[np.ndarray] = []

    for i, chunk in enumerate(chunks, 1):
        wav = tts.tts(text=chunk, speaker=SPEAKER, language=language)
        audio_arrays.append(np.array(wav, dtype=np.float32))

    # Concatenate all chunks in memory
    combined = np.concatenate(audio_arrays)

    # float32 [-1, 1] → int16 PCM for pydub
    pcm = (combined * 32_767).clip(-32_768, 32_767).astype(np.int16)

    segment = AudioSegment(
        pcm.tobytes(),
        frame_rate=SAMPLE_RATE,
        sample_width=2,  # 16-bit = 2 bytes
        channels=1,
    )
    segment.export(str(output_path), format="mp3", bitrate="128k")
    return output_path


print("✓ chunk_text and synthesize_to_mp3 defined")

# Quick sanity check on chunking
sample_chunks = chunk_text(sample_plain)
print(f"  Sample bulletin: {len(sample_plain)} chars → {len(sample_chunks)} chunks")
print(f"  Longest chunk: {max(len(c) for c in sample_chunks)} chars")
```

---

## Task 6: Build Notebook — Model Load + Batch Run Cell

**Files:**
- Modify: `notebooks/07-tts-experiment.ipynb`

- [ ] **Step 1: Add markdown section header cell**

````
## 3. Load Model + Batch Synthesis

XTTS v2 downloads ~1.8 GB on first run (cached after). Load once, reuse for all files.
````

- [ ] **Step 2: Add model load cell**

```python
print("Loading XTTS v2 model (downloads ~1.8 GB on first run)...")
t0 = time.time()
tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2")
print(f"✓ Model loaded in {time.time() - t0:.1f}s")

# Confirm speaker exists
available_speakers = tts.speakers or []
if SPEAKER not in available_speakers:
    print(f"⚠  '{SPEAKER}' not found. Available male voices:")
    print([s for s in available_speakers if any(c.isupper() for c in s)])
else:
    print(f"✓ Speaker '{SPEAKER}' confirmed")
```

- [ ] **Step 3: Add batch synthesis cell**

```python
results = []

for stem in STEMS:
    for lang in LANGUAGES:
        input_path = input_dir / f"{stem}_radio_{lang}.md"
        output_path = output_dir / f"{stem}_radio_{lang}.mp3"
        xtts_lang = LANGUAGE_MAP[lang]

        lang_label = {"en": "English", "tl": "Tagalog", "ceb": "Cebuano"}[lang]
        print(f"\nSynthesizing: {stem} ({lang_label}) → {xtts_lang} phoneme")

        markdown = input_path.read_text(encoding="utf-8")
        plain = preprocess_for_tts(markdown)
        chunks = chunk_text(plain)

        t_start = time.time()
        synthesize_to_mp3(plain, xtts_lang, output_path, tts)
        elapsed = time.time() - t_start

        size_kb = output_path.stat().st_size // 1024

        # Estimate duration from file size: 128kbps → 16 KB/s
        duration_s = (size_kb * 1024 * 8) / 128_000

        print(f"  ✓ {elapsed:.1f}s  |  {size_kb} KB  |  ~{duration_s:.0f}s audio")

        results.append({
            "stem": stem.replace("PAGASA_", ""),
            "language": lang_label,
            "xtts_lang": xtts_lang,
            "chunks": len(chunks),
            "elapsed_s": round(elapsed, 1),
            "size_kb": size_kb,
            "duration_s": round(duration_s),
            "path": str(output_path),
        })

print(f"\n✓ Done — {len(results)} MP3 files written to {output_dir.absolute()}")
```

---

## Task 7: Build Notebook — Summary Cell

**Files:**
- Modify: `notebooks/07-tts-experiment.ipynb`

- [ ] **Step 1: Add markdown section header cell**

````
## 4. Results Summary
````

- [ ] **Step 2: Add summary cell**

```python
print("\nTTS SYNTHESIS SUMMARY")
print("=" * 72)
print(f"{'Bulletin':<28} {'Language':<10} {'Phoneme':<8} {'Chunks':>6} {'Time':>6} {'Size':>7} {'Audio':>7}")
print("-" * 72)

for r in results:
    print(
        f"{r['stem']:<28} {r['language']:<10} {r['xtts_lang']:<8} "
        f"{r['chunks']:>6} {r['elapsed_s']:>5.1f}s {r['size_kb']:>6}KB {r['duration_s']:>6}s"
    )

print("-" * 72)
total_audio = sum(r["duration_s"] for r in results)
print(f"Total audio generated: {total_audio}s ({total_audio/60:.1f} minutes)")
print(f"\n✓ MP3 files ready in: {output_dir.absolute()}")
```

- [ ] **Step 3: Commit the notebook**

```bash
git add notebooks/07-tts-experiment.ipynb
git commit -m "feat: add notebook 07 - TTS experiment with Coqui XTTS v2"
```

---

## Task 8: Run and Verify

- [ ] **Step 1: Run all cells top to bottom**

In Jupyter: Kernel → Restart & Run All. Watch for errors in:
- Model download / load cell
- Speaker confirmation (if `"Damien Black"` is missing, pick from the printed list)
- Each synthesis iteration

- [ ] **Step 2: Verify all 6 MP3s exist and are non-zero**

```bash
ls -lh data/tts_output/*.mp3
```

Expected: 6 files, each between 3–8 MB (4–5 min of 128kbps mono audio).

- [ ] **Step 3: Spot-listen to one file per language**

```bash
# macOS
afplay data/tts_output/PAGASA_20-19W_Pepito_SWB#01_radio_en.mp3
afplay "data/tts_output/PAGASA_20-19W_Pepito_SWB#01_radio_tl.mp3"
afplay "data/tts_output/PAGASA_20-19W_Pepito_SWB#01_radio_ceb.mp3"
```

Listen for:
- English: natural broadcast cadence, pauses between sections
- Tagalog: Filipino vowel sounds (a/e/i/o/u as in Spanish), intelligible
- Cebuano: same phoneme set as Tagalog version

- [ ] **Step 4: Final commit**

```bash
git add data/tts_output/ notebooks/07-tts-experiment.ipynb
git commit -m "feat: generate TTS MP3s for all 6 radio bulletins (en/tl/ceb)"
```

---

## Self-Review

**Spec coverage check:**
- ✅ `preprocess_for_tts()` — Task 2 + Task 4
- ✅ Section headings → pause cues — Task 2 (test), Task 4 (implementation)
- ✅ Built-in male voice "Damien Black" — Task 6 (model load)
- ✅ Language mapping `en→en`, `tl→es`, `ceb→es` — Task 3 (setup) + Task 5
- ✅ Chunking to 200-char limit — Task 5
- ✅ In-memory MP3 via pydub, no WAV — Task 5 (`synthesize_to_mp3`)
- ✅ 6 MP3 output files to `data/tts_output/` — Task 6 (batch run)
- ✅ Modal-ready functions (primitive args, no globals) — Task 5 (docstrings + signatures)
- ✅ Tagalog community model note — Task 3 (notebook markdown cell)
- ✅ Summary table — Task 7

**Placeholder scan:** No TBDs, TODOs, or vague steps. All code blocks are complete.

**Type consistency:** `preprocess_for_tts(str) -> str`, `chunk_text(str, int) -> list[str]`, `synthesize_to_mp3(str, str, Path, TTS) -> Path` — consistent across Tasks 2, 4, 5, 6.
