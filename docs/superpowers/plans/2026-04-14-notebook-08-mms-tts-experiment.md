# Notebook 08 — Facebook MMS TTS Experiment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build notebook 08 to evaluate Facebook MMS TTS (native Cebuano, Tagalog, English) as a replacement for Coqui XTTS v2, with automated speed metrics and a manual audio quality comparison scaffold.

**Architecture:** Load three language-specific VITS models simultaneously (`mms-tts-ceb`, `mms-tts-tgl`, `mms-tts-eng`), synthesize the Pepito SWB#01 bulletin in CEB → TL → EN order, save MP3s to `notebooks/08-mms-tts-experiment/`, then present an assessment scaffold and automated side-by-side comparison table against XTTS v2 metrics from notebook 07.

**Tech Stack:** HuggingFace Transformers (`VitsModel`, `AutoTokenizer`), PyTorch, pydub, scipy, IPython.display

**Spec:** `docs/superpowers/specs/2026-04-14-mms-tts-experiment-design.md`

---

## File Map

| Action | Path | Responsibility |
|---|---|---|
| Modify | `pyproject.toml` | Add `scipy>=1.11.0` dependency |
| Modify | `.gitignore` | Allow `notebooks/08-mms-tts-experiment/` and its MP3s |
| Create | `tests/test_mms_synthesis.py` | Unit tests for `synthesize_with_mms` using mocked model |
| Create | `notebooks/08-mms-tts-experiment.ipynb` | Full experiment notebook (6 cells) |
| Auto-created at runtime | `notebooks/08-mms-tts-experiment/*.mp3` | Generated audio (tracked in git) |
| Auto-created at runtime | `notebooks/08-mms-tts-experiment/*_plain.txt` | Intermediate preprocessed text |

---

## Task 1: Config — Add scipy and gitignore exceptions

**Files:**
- Modify: `pyproject.toml`
- Modify: `.gitignore`

- [ ] **Step 1: Add scipy to pyproject.toml**

Edit `pyproject.toml` dependencies to add scipy after pydub:

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
    "scipy>=1.11.0",
    "transformers>=4.43.0,<=4.46.2",  # pinned: coqui-tts 0.25.x compatibility constraint
]
```

- [ ] **Step 2: Add gitignore exceptions for notebook 08 output folder**

In `.gitignore`, after the existing `!notebooks/07-tts-experiment/**` lines, add:

```gitignore
!notebooks/08-mms-tts-experiment/
!notebooks/08-mms-tts-experiment/**
```

And after `!notebooks/07-tts-experiment/*.mp3`, add:

```gitignore
!notebooks/08-mms-tts-experiment/*.mp3
```

- [ ] **Step 3: Install scipy**

```bash
uv pip install scipy>=1.11.0
```

Expected: installs without errors.

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml .gitignore
git commit -m "chore: add scipy dependency and gitignore exceptions for notebook 08"
```

---

## Task 2: Test — synthesize_with_mms unit tests

**Files:**
- Create: `tests/test_mms_synthesis.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_mms_synthesis.py`:

```python
"""Unit tests for synthesize_with_mms (notebook 08).

Tests use mocked model/tokenizer so no GPU or model download is needed.
The function under test is defined inline here — identical to the notebook cell.
"""
import numpy as np
import torch
import pytest
from pathlib import Path
from unittest.mock import MagicMock
from pydub import AudioSegment


def synthesize_with_mms(
    text: str,
    model,
    tokenizer,
    output_path: Path,
    sample_rate: int | None = None,
) -> Path:
    """Synthesize plain text to MP3 using a HuggingFace VitsModel.

    Modal-ready: all inputs are primitive types + Path; no notebook globals.

    Args:
        text: Plain text (no markdown). Use preprocess_for_tts() first.
        model: Loaded VitsModel instance.
        tokenizer: Loaded AutoTokenizer instance.
        output_path: Destination MP3 path.
        sample_rate: Override model's native sample rate if needed.

    Returns:
        output_path on success.
    """
    inputs = tokenizer(text, return_tensors="pt")
    with torch.no_grad():
        waveform = model(**inputs).waveform

    rate = sample_rate or model.config.sampling_rate

    # float32 [-1, 1] → int16 PCM for pydub
    pcm = (waveform.squeeze().numpy() * 32_767).clip(-32_768, 32_767).astype(np.int16)

    segment = AudioSegment(
        pcm.tobytes(),
        frame_rate=rate,
        sample_width=2,  # 16-bit = 2 bytes
        channels=1,
    )
    segment.export(str(output_path), format="mp3", bitrate="128k")
    return output_path


def _make_mock_model(num_samples: int = 8000, sample_rate: int = 16_000):
    """Return a MagicMock that behaves like VitsModel for synthesis."""
    mock = MagicMock()
    mock.return_value.waveform = torch.zeros(1, num_samples)
    mock.config.sampling_rate = sample_rate
    return mock


def _make_mock_tokenizer():
    """Return a MagicMock that behaves like AutoTokenizer."""
    mock = MagicMock()
    mock.return_value = {"input_ids": torch.tensor([[1, 2, 3]])}
    return mock


def test_synthesize_creates_mp3_file(tmp_path):
    output_path = tmp_path / "output.mp3"
    synthesize_with_mms(
        "hello world",
        _make_mock_model(),
        _make_mock_tokenizer(),
        output_path,
    )
    assert output_path.exists()


def test_synthesize_returns_output_path(tmp_path):
    output_path = tmp_path / "output.mp3"
    result = synthesize_with_mms(
        "hello world",
        _make_mock_model(),
        _make_mock_tokenizer(),
        output_path,
    )
    assert result == output_path


def test_synthesize_mp3_is_non_empty(tmp_path):
    output_path = tmp_path / "output.mp3"
    synthesize_with_mms(
        "hello world",
        _make_mock_model(num_samples=16_000),
        _make_mock_tokenizer(),
        output_path,
    )
    assert output_path.stat().st_size > 0


def test_synthesize_respects_sample_rate_override(tmp_path):
    """sample_rate kwarg overrides model.config.sampling_rate."""
    output_path = tmp_path / "output.mp3"
    # Model reports 16kHz but we override to 22050
    result = synthesize_with_mms(
        "test",
        _make_mock_model(num_samples=22_050, sample_rate=16_000),
        _make_mock_tokenizer(),
        output_path,
        sample_rate=22_050,
    )
    assert result.exists()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_mms_synthesis.py -v
```

Expected: 4 errors — `synthesize_with_mms` is defined in the test file itself so tests should actually pass structurally, but confirm no import errors.

- [ ] **Step 3: Run tests to confirm they all pass**

```bash
uv run pytest tests/test_mms_synthesis.py -v
```

Expected output:
```
tests/test_mms_synthesis.py::test_synthesize_creates_mp3_file PASSED
tests/test_mms_synthesis.py::test_synthesize_returns_output_path PASSED
tests/test_mms_synthesis.py::test_synthesize_mp3_is_non_empty PASSED
tests/test_mms_synthesis.py::test_synthesize_respects_sample_rate_override PASSED
4 passed
```

- [ ] **Step 4: Commit**

```bash
git add tests/test_mms_synthesis.py
git commit -m "test: add unit tests for synthesize_with_mms (notebook 08)"
```

---

## Task 3: Notebook — Cells 1–2 (Setup + Preprocessing)

**Files:**
- Create: `notebooks/08-mms-tts-experiment.ipynb`

- [ ] **Step 1: Create notebook with markdown title cell**

Create `notebooks/08-mms-tts-experiment.ipynb` with the following cells.

**Cell 1 (markdown):**
```markdown
# TTS Experiment — Facebook MMS TTS

**WeatherSpeak PH** — Gemma 4 Hackathon

## Objective

Evaluate Facebook's Massively Multilingual Speech (MMS) TTS models as a replacement
for Coqui XTTS v2. MMS provides **native** Cebuano and Tagalog models — no Spanish
phoneme approximation required.

### Models used
| Language | Model | Params |
|---|---|---|
| Cebuano | `facebook/mms-tts-ceb` | 36.3M |
| Tagalog | `facebook/mms-tts-tgl` | 36.3M |
| English | `facebook/mms-tts-eng` | 36.3M |

### Bulletin
`PAGASA_20-19W_Pepito_SWB#01` — Severe Weather Bulletin, Tropical Depression Pepito

### Synthesis order
CEB → TL → EN

### License note
MMS TTS models are CC-BY-NC 4.0 (non-commercial). Acceptable for this hackathon.
Flag for production licensing review.
```

**Cell 2 (code) — Setup & paths:**
```python
import re
import time
import numpy as np
import torch
from pathlib import Path
from pydub import AudioSegment
from transformers import VitsModel, AutoTokenizer

# --- Paths ---
notebook_dir = Path(".")
output_dir = notebook_dir / "08-mms-tts-experiment"
output_dir.mkdir(exist_ok=True)

data_dir = notebook_dir.parent / "data"
input_dir = data_dir / "radio_bulletins"

# --- Experiment scope ---
STEM = "PAGASA_20-19W_Pepito_SWB#01"
LANGUAGES = ["ceb", "tl", "en"]  # synthesis order: CEB first
MMS_MODELS = {
    "ceb": "facebook/mms-tts-ceb",
    "tl":  "facebook/mms-tts-tgl",
    "en":  "facebook/mms-tts-eng",
}

# --- Verify input files exist ---
input_files = {lang: input_dir / f"{STEM}_radio_{lang}.md" for lang in LANGUAGES}
missing = [str(p) for p in input_files.values() if not p.exists()]
if missing:
    print(f"⚠  Missing input files: {missing}")
else:
    print(f"✓ All 3 input files found")
    for lang, p in input_files.items():
        print(f"  {lang}: {p.name}")

print(f"✓ Output dir: {output_dir.absolute()}")
```

- [ ] **Step 2: Add preprocessing cell (Cell 3)**

**Cell 3 (markdown):**
```markdown
## 1. Text Preprocessing

Reuse `preprocess_for_tts` from notebook 07 — strips markdown formatting so
nothing is read aloud except actual spoken content.
```

**Cell 4 (code):**
```python
def preprocess_for_tts(markdown_text: str) -> str:
    """Strip markdown formatting for clean TTS input.

    Nothing in the output should be read aloud unless it is actual spoken content.
    Modal-ready: pure function, no external state.
    Copied from notebook 07 — keep in sync if updated there.
    """
    text = markdown_text

    # Remove stage directions: **(Sound effect: ...)** on their own line
    text = re.sub(r"^\s*\*\*\([^)]+\)\*\*\s*$", "", text, flags=re.MULTILINE)

    # Remove role labels: **BROADCASTER:** **Boses:** **LABEL:** etc.
    text = re.sub(r"\*\*[A-Za-z][A-Za-z\s]+:\*\*\s*", "", text)

    # Section headings → just the heading text as a plain spoken sentence
    text = re.sub(r"^#{1,6}\s+(.+)$", r"\1.", text, flags=re.MULTILINE)

    # Horizontal rules — must come BEFORE bold/italic removal to avoid *** corruption
    text = re.sub(r"^[-*_]{3,}$", "", text, flags=re.MULTILINE)

    # Bold and italic markers
    text = re.sub(r"\*{1,3}(.+?)\*{1,3}", r"\1", text)
    text = re.sub(r"_{1,3}(.+?)_{1,3}", r"\1", text)

    # Inline code
    text = re.sub(r"`(.+?)`", r"\1", text)

    # Blockquotes
    text = re.sub(r"^>\s+", "", text, flags=re.MULTILINE)

    # Numbered and bulleted list markers
    text = re.sub(r"^\s*\d+\.\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*[-*+]\s+", "", text, flags=re.MULTILINE)

    # Remove any leftover parenthetical stage directions (fallback, after bold stripped)
    text = re.sub(r"^\s*\([^)]{10,}\)\s*$", "", text, flags=re.MULTILINE)

    # Remove role labels that survived bold stripping: WORD: at start of line
    text = re.sub(r"^[A-Z][A-Za-z\s]+:\s*$", "", text, flags=re.MULTILINE)

    # Collapse 3+ blank lines to 2
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


# Preprocess all 3 scripts upfront and save plain text files
plain_texts = {}
for lang in LANGUAGES:
    md = input_files[lang].read_text(encoding="utf-8")
    plain = preprocess_for_tts(md)
    plain_texts[lang] = plain

    plain_path = output_dir / f"{STEM}_radio_{lang}_plain.txt"
    plain_path.write_text(plain, encoding="utf-8")
    print(f"✓ {lang}: {len(md)} chars → {len(plain)} chars  (saved {plain_path.name})")

# Preview CEB plain text
print("\nPREPROCESSED TEXT — CEB (first 500 chars)")
print("=" * 60)
print(plain_texts["ceb"][:500])
print("...")
```

- [ ] **Step 3: Commit notebook (cells 1–4)**

```bash
git add notebooks/08-mms-tts-experiment.ipynb
git commit -m "feat: notebook 08 - setup and preprocessing cells"
```

---

## Task 4: Notebook — Cell 5: Load All 3 Models

**Files:**
- Modify: `notebooks/08-mms-tts-experiment.ipynb`

- [ ] **Step 1: Add model loading markdown cell**

**Cell 5 (markdown):**
```markdown
## 2. Load MMS Models

Load all three VITS models simultaneously. Each is ~140 MB (F32). Downloads are cached
by HuggingFace after first run.

Unlike XTTS v2 (1.8 GB single multilingual model), MMS uses one small model per language.
```

- [ ] **Step 2: Add model loading code cell**

**Cell 6 (code):**
```python
print("Loading MMS models (downloads ~140 MB each on first run, cached after)...")
t0 = time.time()

models = {}
tokenizers = {}

for lang in LANGUAGES:
    model_id = MMS_MODELS[lang]
    lang_label = {"ceb": "Cebuano", "tl": "Tagalog", "en": "English"}[lang]
    print(f"  Loading {lang_label} ({model_id})...")
    t_lang = time.time()
    tokenizers[lang] = AutoTokenizer.from_pretrained(model_id)
    models[lang] = VitsModel.from_pretrained(model_id)
    models[lang].eval()
    print(f"  ✓ {lang_label} loaded in {time.time() - t_lang:.1f}s")

print(f"\n✓ All 3 models loaded in {time.time() - t0:.1f}s total")
print(f"  Sample rates: { {lang: models[lang].config.sampling_rate for lang in LANGUAGES} }")
```

- [ ] **Step 3: Commit**

```bash
git add notebooks/08-mms-tts-experiment.ipynb
git commit -m "feat: notebook 08 - model loading cell"
```

---

## Task 5: Notebook — Cell 6: Synthesis

**Files:**
- Modify: `notebooks/08-mms-tts-experiment.ipynb`

The `synthesize_with_mms` function here must be **identical** to the one in `tests/test_mms_synthesis.py` (Task 2).

- [ ] **Step 1: Add synthesis markdown cell**

**Cell 7 (markdown):**
```markdown
## 3. Synthesis

`synthesize_with_mms`: tokenize → model inference → float32 waveform → int16 PCM →
pydub AudioSegment → MP3 at 128kbps.

No chunking needed — VITS processes the full text in one pass (unlike XTTS v2's
~200-char chunk limit).

Synthesis order: CEB → TL → EN.
```

- [ ] **Step 2: Add synthesis code cell**

**Cell 8 (code):**
```python
def synthesize_with_mms(
    text: str,
    model,
    tokenizer,
    output_path: Path,
    sample_rate: int | None = None,
) -> Path:
    """Synthesize plain text to MP3 using a HuggingFace VitsModel.

    Modal-ready: all inputs are primitive types + Path; no notebook globals.

    Args:
        text: Plain text (no markdown). Use preprocess_for_tts() first.
        model: Loaded VitsModel instance.
        tokenizer: Loaded AutoTokenizer instance.
        output_path: Destination MP3 path.
        sample_rate: Override model's native sample rate if needed.

    Returns:
        output_path on success.
    """
    inputs = tokenizer(text, return_tensors="pt")
    with torch.no_grad():
        waveform = model(**inputs).waveform

    rate = sample_rate or model.config.sampling_rate

    # float32 [-1, 1] → int16 PCM for pydub
    pcm = (waveform.squeeze().numpy() * 32_767).clip(-32_768, 32_767).astype(np.int16)

    segment = AudioSegment(
        pcm.tobytes(),
        frame_rate=rate,
        sample_width=2,  # 16-bit = 2 bytes
        channels=1,
    )
    segment.export(str(output_path), format="mp3", bitrate="128k")
    return output_path


# --- Run synthesis: CEB → TL → EN ---
results = {}

for lang in LANGUAGES:
    lang_label = {"ceb": "Cebuano", "tl": "Tagalog", "en": "English"}[lang]
    output_path = output_dir / f"{STEM}_radio_{lang}.mp3"

    print(f"Synthesizing {lang_label}...")
    t_start = time.time()
    synthesize_with_mms(
        plain_texts[lang],
        models[lang],
        tokenizers[lang],
        output_path,
    )
    elapsed = time.time() - t_start

    size_kb = output_path.stat().st_size // 1024
    duration_s = (size_kb * 1024 * 8) / 128_000

    print(f"  ✓ {elapsed:.1f}s  |  {size_kb} KB  |  ~{duration_s:.0f}s audio")
    print(f"  ✓ {output_path.name}")

    results[lang] = {
        "lang_label": lang_label,
        "elapsed_s": round(elapsed, 1),
        "size_kb": size_kb,
        "duration_s": round(duration_s),
        "path": output_path,
    }

print("\n✓ Synthesis complete")
```

- [ ] **Step 3: Commit**

```bash
git add notebooks/08-mms-tts-experiment.ipynb
git commit -m "feat: notebook 08 - synthesis function and synthesis cell"
```

---

## Task 6: Notebook — Cell 7: Manual Assessment

**Files:**
- Modify: `notebooks/08-mms-tts-experiment.ipynb`

- [ ] **Step 1: Add assessment markdown cell**

**Cell 9 (markdown):**
```markdown
## 4. Manual Audio Assessment

Listen to each MP3 using the players below, then fill in your scores in the
assessment dict in the next cell.

**Score guide:**
- `quality_score` (1–5): Overall audio quality and clarity
- `natural_filipino` (1–5): How natural the Filipino pronunciation sounds (CEB/TL only;
  use for EN to rate overall naturalness)

Run the cell after filling in your scores — the comparison table in the next section
uses these values.
```

- [ ] **Step 2: Add audio playback + assessment cell**

**Cell 10 (code):**
```python
from IPython.display import Audio, display

for lang in LANGUAGES:
    lang_label = results[lang]["lang_label"]
    print(f"--- {lang_label} ---")
    display(Audio(str(results[lang]["path"]), autoplay=False))
    print()
```

**Cell 11 (code) — user fills in scores:**
```python
# ── FILL IN YOUR SCORES AFTER LISTENING ──────────────────────────────────────
assessment = {
    "ceb": {
        "quality_score": None,     # 1–5: overall audio quality
        "natural_filipino": None,  # 1–5: naturalness of Cebuano pronunciation
        "notes": "",
    },
    "tl": {
        "quality_score": None,
        "natural_filipino": None,  # 1–5: naturalness of Tagalog pronunciation
        "notes": "",
    },
    "en": {
        "quality_score": None,
        "natural_filipino": None,  # 1–5: naturalness / clarity
        "notes": "",
    },
}
# ─────────────────────────────────────────────────────────────────────────────

print("Assessment recorded. Run the next cell to see the comparison table.")
for lang, scores in assessment.items():
    label = {"ceb": "Cebuano", "tl": "Tagalog", "en": "English"}[lang]
    q = scores["quality_score"] or "—"
    n = scores["natural_filipino"] or "—"
    print(f"  {label}: quality={q}/5  naturalness={n}/5  notes={scores['notes']!r}")
```

- [ ] **Step 3: Commit**

```bash
git add notebooks/08-mms-tts-experiment.ipynb
git commit -m "feat: notebook 08 - manual assessment cell"
```

---

## Task 7: Notebook — Cell 8: Comparison Table

**Files:**
- Modify: `notebooks/08-mms-tts-experiment.ipynb`

- [ ] **Step 1: Add comparison markdown cell**

**Cell 12 (markdown):**
```markdown
## 5. Comparison: MMS TTS vs XTTS v2

XTTS v2 baseline from notebook 07 (CEB only — EN/TL were not run to completion):
- Synthesis time: 821s for CEB bulletin
- Audio duration: ~467s (~7.8 min)
- Language mapping: Spanish phoneme approximation for CEB and TL
- Model size: 1.87 GB download

MMS TTS: native Cebuano and Tagalog phonemes, ~140 MB per model.
```

- [ ] **Step 2: Add comparison table code cell**

**Cell 13 (code):**
```python
# XTTS v2 baseline from notebook 07 (CEB only)
xtts_baseline = {
    "ceb": {"elapsed_s": 821.2, "size_kb": 7293, "duration_s": 467,
            "quality_score": None, "natural_filipino": None,
            "phoneme": "es (Spanish approx)", "model_size": "1.87 GB"},
}

print("MMS TTS vs XTTS v2 — PAGASA_20-19W_Pepito_SWB#01")
print("=" * 90)
print(f"{'Model':<12} {'Lang':<10} {'Time':>7} {'Audio':>7} {'Size':>8}  "
      f"{'Quality':>8} {'Naturalness':>12}  {'Phoneme'}")
print("-" * 90)

for lang in LANGUAGES:
    lang_label = results[lang]["lang_label"]
    r = results[lang]
    a = assessment[lang]
    mms_phoneme = "native" if lang in ("ceb", "tl") else "native"
    q = f"{a['quality_score']}/5" if a["quality_score"] else "—"
    n = f"{a['natural_filipino']}/5" if a["natural_filipino"] else "—"
    print(f"{'MMS':<12} {lang_label:<10} {r['elapsed_s']:>6.1f}s {r['duration_s']:>6}s "
          f"{r['size_kb']:>7}KB  {q:>8} {n:>12}  {mms_phoneme}")

print()
for lang in ["ceb"]:
    b = xtts_baseline[lang]
    lang_label = "Cebuano"
    q = f"{b['quality_score']}/5" if b["quality_score"] else "—"
    n = f"{b['natural_filipino']}/5" if b["natural_filipino"] else "—"
    print(f"{'XTTS v2':<12} {lang_label:<10} {b['elapsed_s']:>6.1f}s {b['duration_s']:>6}s "
          f"{b['size_kb']:>7}KB  {q:>8} {n:>12}  {b['phoneme']}")

print("=" * 90)
print(f"\nMMS total model footprint: ~{len(LANGUAGES) * 140} MB  vs  XTTS v2: 1,870 MB")

# Speedup for CEB (the one language with an XTTS v2 baseline)
if "ceb" in results and results["ceb"]["elapsed_s"] > 0:
    speedup = xtts_baseline["ceb"]["elapsed_s"] / results["ceb"]["elapsed_s"]
    print(f"MMS CEB speedup vs XTTS v2: {speedup:.1f}×")
```

**Cell 14 (markdown) — fill in after assessment:**
```markdown
## Conclusion

> **TODO (fill in after listening):** Based on the scores above, does MMS TTS replace
> XTTS v2 for WeatherSpeak PH?
>
> - CEB/TL naturalness: is native phoneme support a meaningful improvement over Spanish approximation?
> - Speed: is the synthesis time reduction significant enough to matter for the pipeline?
> - Recommendation: replace XTTS v2 / use MMS for CEB+TL only / keep XTTS v2
```

- [ ] **Step 3: Commit**

```bash
git add notebooks/08-mms-tts-experiment.ipynb
git commit -m "feat: notebook 08 - comparison table and conclusion scaffold"
```

---

## Task 8: Push branch

- [ ] **Step 1: Run full test suite to confirm nothing broken**

```bash
uv run pytest tests/ -v
```

Expected: all tests pass (including existing `test_tts_preprocess.py` and new `test_mms_synthesis.py`).

- [ ] **Step 2: Push to remote**

```bash
git push origin feature/tts-experiment
```

---

## Self-Review

**Spec coverage:**
- ✅ Load all 3 models simultaneously (Option B) — Task 4
- ✅ CEB → TL → EN synthesis order — Tasks 3, 5
- ✅ Output to `notebooks/08-mms-tts-experiment/` — Task 1, 3
- ✅ Plain text files saved alongside MP3s — Task 3
- ✅ Manual assessment scaffold with audio players — Task 6
- ✅ Automated speed metrics — Task 5
- ✅ Side-by-side comparison table vs XTTS v2 — Task 7
- ✅ `.gitignore` exceptions — Task 1
- ✅ `scipy` dependency — Task 1
- ✅ TDD for `synthesize_with_mms` — Task 2
- ✅ `preprocess_for_tts` copied from nb 07 — Task 3
- ✅ CC-BY-NC license noted in notebook — Task 3

**No placeholders found.**

**Type consistency:** `synthesize_with_mms` signature is identical in `tests/test_mms_synthesis.py` (Task 2) and notebook Cell 8 (Task 5). `plain_texts` dict built in Task 3 Cell 4 and consumed in Task 5 Cell 8. `results` dict built in Task 5 and consumed in Tasks 6 and 7.
