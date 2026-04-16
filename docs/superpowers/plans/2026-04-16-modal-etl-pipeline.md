# Modal ETL Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deploy the WeatherSpeak PH 3-step ETL pipeline (PDF → OCR → radio scripts → MP3) as a batch Modal app that processes the newest N PAGASA severe weather events and stores all artifacts in Modal Volumes.

**Architecture:** Three separate Modal functions — `Step1OCR` (GPU, Ollama + Gemma 4 E4B), `Step2Scripts` (GPU, Ollama + Gemma 4 E4B), and `step3_tts` (CPU, MMS + SpeechT5) — chained sequentially per bulletin by a local entrypoint. TTS models are behind a `TTSSynthesizer` protocol so any model can be swapped by updating one line in config. All artifacts (markdown, TTS text, MP3) are stored in a Modal Volume keyed by bulletin stem.

**Tech Stack:** Modal, Ollama, `gemma4:e4b`, `facebook/mms-tts-ceb`, `facebook/mms-tts-tgl`, `microsoft/speecht5_tts`, `transformers`, `pydub`, `pdf2image`, `requests`, `uv`

**Design spec:** `docs/superpowers/specs/2026-04-16-modal-etl-design.md`

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `modal_etl/__init__.py` | Create | Package marker |
| `modal_etl/app.py` | Create | Modal App, Volume, Image definitions |
| `modal_etl/config.py` | Create | Constants: N, languages, volume names, mount paths |
| `modal_etl/bulletin_selector.py` | Create | GitHub API → newest N events → latest bulletin each |
| `modal_etl/synthesizers/__init__.py` | Create | Package marker |
| `modal_etl/synthesizers/base.py` | Create | `TTSSynthesizer` Protocol |
| `modal_etl/synthesizers/mms.py` | Create | `MMSSynthesizer` wrapping MMS VITS models |
| `modal_etl/synthesizers/speecht5.py` | Create | `SpeechT5Synthesizer` wrapping SpeechT5 + HiFiGAN |
| `modal_etl/step3_tts.py` | Create | Sentence prep utilities + `step3_tts` Modal function |
| `modal_etl/step1_ocr.py` | Create | `Step1OCR` Modal class — Ollama OCR → `ocr.md` |
| `modal_etl/step2_scripts.py` | Create | `Step2Scripts` Modal class — radio `.md` + TTS `.txt` |
| `modal_etl/setup_volumes.py` | Create | One-time volume init: pull Ollama model, cache HF weights |
| `modal_etl/run_batch.py` | Create | `@app.local_entrypoint` — orchestrates full pipeline |
| `pyproject.toml` | Modify | Add `modal`, `pdf2image`, `requests` dependencies |
| `tests/test_bulletin_selector.py` | Create | Unit tests for bulletin selection logic |
| `tests/test_synthesizers_mms.py` | Create | Unit tests for `MMSSynthesizer` (mocked model) |
| `tests/test_synthesizers_speecht5.py` | Create | Unit tests for `SpeechT5Synthesizer` (mocked model) |
| `tests/test_step3_sentences.py` | Create | Unit tests for sentence prep utilities |

---

## Task 1: Project Scaffold + Config + Modal App

**Files:**
- Create: `modal_etl/__init__.py`
- Create: `modal_etl/synthesizers/__init__.py`
- Create: `modal_etl/config.py`
- Create: `modal_etl/app.py`
- Modify: `pyproject.toml`

- [ ] **Step 1: Create package directories**

```bash
mkdir -p modal_etl/synthesizers
touch modal_etl/__init__.py modal_etl/synthesizers/__init__.py
```

- [ ] **Step 2: Add Modal and pdf2image to pyproject.toml**

In `pyproject.toml`, update the dependencies list:

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
    "modal>=0.73.0",
    "pdf2image>=1.17.0",
    "requests>=2.32.0",
]
```

- [ ] **Step 3: Install new dependencies**

```bash
uv pip install modal pdf2image requests
```

Expected: packages install without errors.

- [ ] **Step 4: Write `modal_etl/config.py`**

```python
from pathlib import Path

# Bulletin selection
N_EVENTS: int = 10

# Languages processed by the pipeline
LANGUAGES: list[str] = ["ceb", "tl", "en"]

# Modal Volume names (created on first run if missing)
OLLAMA_VOLUME_NAME = "weatherspeak-ollama"
TTS_VOLUME_NAME = "weatherspeak-tts-models"
OUTPUT_VOLUME_NAME = "weatherspeak-output"

# Mount paths inside Modal containers
OLLAMA_MODELS_PATH = Path("/ollama/models")
TTS_MODELS_PATH = Path("/tts-models")
OUTPUT_PATH = Path("/output")

# Gemma model served by Ollama
GEMMA_MODEL = "gemma4:e4b"

# GitHub archive
ARCHIVE_REPO = "pagasa-parser/bulletin-archive"
ARCHIVE_RAW_BASE = "https://raw.githubusercontent.com/pagasa-parser/bulletin-archive/main"
ARCHIVE_API_URL = (
    "https://api.github.com/repos/pagasa-parser/bulletin-archive/"
    "git/trees/HEAD?recursive=1"
)
```

- [ ] **Step 5: Write `modal_etl/app.py`**

```python
import modal
from modal_etl.config import (
    OLLAMA_VOLUME_NAME,
    TTS_VOLUME_NAME,
    OUTPUT_VOLUME_NAME,
    OLLAMA_MODELS_PATH,
    TTS_MODELS_PATH,
    OUTPUT_PATH,
)

app = modal.App("weatherspeak-etl")

# Persistent volumes — created on first access
ollama_volume = modal.Volume.from_name(OLLAMA_VOLUME_NAME, create_if_missing=True)
tts_volume = modal.Volume.from_name(TTS_VOLUME_NAME, create_if_missing=True)
output_volume = modal.Volume.from_name(OUTPUT_VOLUME_NAME, create_if_missing=True)

# Volume mounts used by GPU (Ollama) functions
OLLAMA_MOUNTS = {
    str(OLLAMA_MODELS_PATH): ollama_volume,
    str(OUTPUT_PATH): output_volume,
}

# Volume mounts used by CPU (TTS) function
TTS_MOUNTS = {
    str(TTS_MODELS_PATH): tts_volume,
    str(OUTPUT_PATH): output_volume,
}

# Container image for steps 1 & 2 (Ollama + Gemma 4)
ollama_image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("curl", "poppler-utils", "ffmpeg")
    .run_commands("curl -fsSL https://ollama.ai/install.sh | sh")
    .pip_install(
        "requests>=2.32.0",
        "Pillow>=10.0.0",
        "pdf2image>=1.17.0",
    )
)

# Container image for step 3 (MMS + SpeechT5)
tts_image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("ffmpeg")
    .pip_install(
        "torch>=2.2.0",
        "transformers>=4.43.0,<=4.46.2",
        "pydub>=0.25.1",
        "numpy>=1.26.0",
        "datasets>=2.19.0",
    )
)
```

- [ ] **Step 6: Verify imports are clean**

```bash
uv run python -c "from modal_etl.config import N_EVENTS; from modal_etl.app import app; print('OK')"
```

Expected: `OK`

- [ ] **Step 7: Commit**

```bash
git add modal_etl/ pyproject.toml uv.lock
git commit -m "feat: scaffold modal_etl package with config, volumes, and container images"
```

---

## Task 2: Bulletin Selector

**Files:**
- Create: `modal_etl/bulletin_selector.py`
- Create: `tests/test_bulletin_selector.py`

The selector hits the GitHub API, groups PDF files by storm event name, picks the latest bulletin per event, then returns the newest N events.

Filename format: `PAGASA_{storm_id}_{storm_name}_{bulletin_type}#{seq}.pdf`
- `storm_name` (e.g. `Pepito`, `Basyang`) is the event identifier
- `{seq}` (e.g. `01`, `12`) is the bulletin sequence number within the event
- `storm_id` (e.g. `20-19W`, `22-TC02`) encodes recency — higher values are more recent

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_bulletin_selector.py
import pytest
from unittest.mock import patch
from modal_etl.bulletin_selector import (
    parse_bulletin_filename,
    group_by_event,
    get_latest_bulletins,
    BulletinInfo,
)


# --- parse_bulletin_filename ---

def test_parse_swb_bulletin():
    info = parse_bulletin_filename("PAGASA_20-19W_Pepito_SWB#01.pdf")
    assert info is not None
    assert info.stem == "PAGASA_20-19W_Pepito_SWB#01"
    assert info.event_name == "Pepito"
    assert info.storm_id == "20-19W"
    assert info.bulletin_seq == 1


def test_parse_tca_bulletin():
    info = parse_bulletin_filename("PAGASA_22-TC02_Basyang_TCA#05.pdf")
    assert info is not None
    assert info.event_name == "Basyang"
    assert info.bulletin_seq == 5


def test_parse_returns_none_for_non_bulletin():
    assert parse_bulletin_filename("README.md") is None
    assert parse_bulletin_filename("PAGASA_random_garbage.pdf") is None


# --- group_by_event ---

def test_group_by_event_groups_same_storm():
    infos = [
        parse_bulletin_filename("PAGASA_20-19W_Pepito_SWB#01.pdf"),
        parse_bulletin_filename("PAGASA_20-19W_Pepito_SWB#02.pdf"),
        parse_bulletin_filename("PAGASA_22-TC02_Basyang_TCA#01.pdf"),
    ]
    groups = group_by_event(infos)
    assert "Pepito" in groups
    assert "Basyang" in groups
    assert len(groups["Pepito"]) == 2
    assert len(groups["Basyang"]) == 1


def test_group_by_event_latest_has_highest_seq():
    infos = [
        parse_bulletin_filename("PAGASA_20-19W_Pepito_SWB#01.pdf"),
        parse_bulletin_filename("PAGASA_20-19W_Pepito_SWB#03.pdf"),
        parse_bulletin_filename("PAGASA_20-19W_Pepito_SWB#02.pdf"),
    ]
    groups = group_by_event(infos)
    latest = max(groups["Pepito"], key=lambda b: b.bulletin_seq)
    assert latest.bulletin_seq == 3


# --- get_latest_bulletins (mocked GitHub API) ---

FAKE_TREE = {
    "tree": [
        {"path": "bulletins/PAGASA_20-19W_Pepito_SWB#01.pdf", "type": "blob"},
        {"path": "bulletins/PAGASA_20-19W_Pepito_SWB#02.pdf", "type": "blob"},
        {"path": "bulletins/PAGASA_22-TC02_Basyang_TCA#01.pdf", "type": "blob"},
        {"path": "README.md", "type": "blob"},
    ]
}


def test_get_latest_bulletins_returns_n_events():
    with patch("modal_etl.bulletin_selector.requests.get") as mock_get:
        mock_get.return_value.json.return_value = FAKE_TREE
        mock_get.return_value.raise_for_status = lambda: None
        results = get_latest_bulletins(n=2)
    assert len(results) == 2


def test_get_latest_bulletins_returns_latest_per_event():
    with patch("modal_etl.bulletin_selector.requests.get") as mock_get:
        mock_get.return_value.json.return_value = FAKE_TREE
        mock_get.return_value.raise_for_status = lambda: None
        results = get_latest_bulletins(n=10)
    pepito = next((r for r in results if "Pepito" in r.stem), None)
    assert pepito is not None
    assert pepito.bulletin_seq == 2  # latest, not #01


def test_get_latest_bulletins_pdf_url_is_raw_github():
    with patch("modal_etl.bulletin_selector.requests.get") as mock_get:
        mock_get.return_value.json.return_value = FAKE_TREE
        mock_get.return_value.raise_for_status = lambda: None
        results = get_latest_bulletins(n=10)
    for r in results:
        assert r.pdf_url.startswith("https://raw.githubusercontent.com")
        assert r.pdf_url.endswith(".pdf")
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
uv run pytest tests/test_bulletin_selector.py -v
```

Expected: `ImportError` — `bulletin_selector` does not exist yet.

- [ ] **Step 3: Write `modal_etl/bulletin_selector.py`**

```python
import re
import requests
from dataclasses import dataclass
from modal_etl.config import ARCHIVE_API_URL, ARCHIVE_RAW_BASE


@dataclass
class BulletinInfo:
    stem: str          # filename without .pdf
    pdf_url: str       # raw GitHub download URL
    event_name: str    # storm name (e.g. "Pepito")
    storm_id: str      # e.g. "20-19W" or "22-TC02"
    bulletin_seq: int  # sequence number (#NN)


_FILENAME_RE = re.compile(
    r"^PAGASA_([^_]+)_([A-Za-z]+)_(?:SWB|TCA|TCB|TCW)#(\d+)\.pdf$"
)


def parse_bulletin_filename(filename: str) -> BulletinInfo | None:
    """Parse a PAGASA bulletin filename. Returns None if not a valid bulletin."""
    name = filename.split("/")[-1]  # strip any directory prefix
    m = _FILENAME_RE.match(name)
    if not m:
        return None
    storm_id, event_name, seq_str = m.group(1), m.group(2), m.group(3)
    stem = name[: -len(".pdf")]
    return BulletinInfo(
        stem=stem,
        pdf_url="",  # filled in by get_latest_bulletins
        event_name=event_name,
        storm_id=storm_id,
        bulletin_seq=int(seq_str),
    )


def group_by_event(bulletins: list[BulletinInfo]) -> dict[str, list[BulletinInfo]]:
    """Group bulletins by storm event name."""
    groups: dict[str, list[BulletinInfo]] = {}
    for b in bulletins:
        groups.setdefault(b.event_name, []).append(b)
    return groups


def get_latest_bulletins(n: int) -> list[BulletinInfo]:
    """Return the latest bulletin for each of the newest N severe weather events.

    Recency is determined by storm_id lexicographic order (higher = more recent).
    """
    resp = requests.get(ARCHIVE_API_URL)
    resp.raise_for_status()
    tree = resp.json().get("tree", [])

    bulletins = []
    for node in tree:
        if node.get("type") != "blob":
            continue
        path = node["path"]
        info = parse_bulletin_filename(path)
        if info is None:
            continue
        # Build raw GitHub URL from the path in the tree
        info.pdf_url = f"{ARCHIVE_RAW_BASE}/{path}"
        bulletins.append(info)

    groups = group_by_event(bulletins)

    # Pick latest bulletin per event
    latest_per_event: list[BulletinInfo] = []
    for event_bulletins in groups.values():
        latest = max(event_bulletins, key=lambda b: b.bulletin_seq)
        latest_per_event.append(latest)

    # Sort events by storm_id descending (lexicographic — higher = more recent)
    latest_per_event.sort(key=lambda b: b.storm_id, reverse=True)

    return latest_per_event[:n]
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
uv run pytest tests/test_bulletin_selector.py -v
```

Expected: all 8 tests `PASSED`.

- [ ] **Step 5: Commit**

```bash
git add modal_etl/bulletin_selector.py tests/test_bulletin_selector.py
git commit -m "feat: add bulletin selector with GitHub API + event grouping"
```

---

## Task 3: TTSSynthesizer Protocol + MMSSynthesizer

**Files:**
- Create: `modal_etl/synthesizers/base.py`
- Create: `modal_etl/synthesizers/mms.py`
- Create: `tests/test_synthesizers_mms.py`

- [ ] **Step 1: Write `modal_etl/synthesizers/base.py`**

```python
from pathlib import Path
from typing import Protocol, runtime_checkable


@runtime_checkable
class TTSSynthesizer(Protocol):
    """Common interface for all TTS backends.

    Implementors must provide:
    - load(): initialise model weights into memory
    - synthesize(): convert sentences to an MP3 file
    """

    def load(self) -> None:
        """Load model weights. Called once at container startup."""
        ...

    def synthesize(
        self,
        sentences: list[tuple[str, bool]],
        output_path: Path,
    ) -> Path:
        """Synthesize sentences to an MP3 file.

        Args:
            sentences: list of (text, is_paragraph_end) tuples.
                       is_paragraph_end=True triggers a longer inter-sentence pause.
            output_path: destination path for the MP3 file.

        Returns:
            output_path on success.
        """
        ...
```

- [ ] **Step 2: Write the failing MMSSynthesizer tests**

```python
# tests/test_synthesizers_mms.py
import pytest
import torch
import numpy as np
from pathlib import Path
from unittest.mock import MagicMock, patch
from pydub import AudioSegment

from modal_etl.synthesizers.mms import MMSSynthesizer
from modal_etl.synthesizers.base import TTSSynthesizer


def _mock_vits_model(num_samples: int = 8000, sample_rate: int = 16_000):
    mock = MagicMock()
    mock.return_value.waveform = torch.zeros(1, num_samples)
    mock.config.sampling_rate = sample_rate
    return mock


def _mock_tokenizer():
    mock = MagicMock()
    mock.return_value = {"input_ids": torch.tensor([[1, 2, 3]])}
    return mock


def _loaded_synthesizer(model_id: str = "facebook/mms-tts-ceb") -> MMSSynthesizer:
    """Return an MMSSynthesizer with mocked model/tokenizer already loaded."""
    synth = MMSSynthesizer(model_id)
    synth._model = _mock_vits_model()
    synth._tokenizer = _mock_tokenizer()
    return synth


def test_mms_synthesizer_satisfies_protocol():
    synth = MMSSynthesizer("facebook/mms-tts-ceb")
    assert isinstance(synth, TTSSynthesizer)


def test_mms_synthesize_creates_mp3(tmp_path):
    synth = _loaded_synthesizer()
    out = tmp_path / "out.mp3"
    synth.synthesize([("maayong buntag", True)], out)
    assert out.exists()
    assert out.stat().st_size > 0


def test_mms_synthesize_returns_output_path(tmp_path):
    synth = _loaded_synthesizer()
    out = tmp_path / "out.mp3"
    result = synth.synthesize([("maayong buntag", True)], out)
    assert result == out


def test_mms_synthesize_paragraph_pause_longer_than_sentence_pause(tmp_path):
    synth_s = _loaded_synthesizer()
    synth_p = _loaded_synthesizer()
    out_s = tmp_path / "sentence.mp3"
    out_p = tmp_path / "paragraph.mp3"
    synth_s.synthesize([("hello", False)], out_s)
    synth_p.synthesize([("hello", True)], out_p)
    dur_s = len(AudioSegment.from_mp3(str(out_s)))
    dur_p = len(AudioSegment.from_mp3(str(out_p)))
    assert dur_p > dur_s


def test_mms_synthesize_raises_on_empty_sentences(tmp_path):
    synth = _loaded_synthesizer()
    with pytest.raises(ValueError, match="empty"):
        synth.synthesize([], tmp_path / "out.mp3")


def test_mms_synthesize_two_sentences_longer_than_one(tmp_path):
    synth = _loaded_synthesizer()
    out1 = tmp_path / "one.mp3"
    out2 = tmp_path / "two.mp3"
    synth.synthesize([("hello", True)], out1)
    synth.synthesize([("hello", False), ("world", True)], out2)
    dur1 = len(AudioSegment.from_mp3(str(out1)))
    dur2 = len(AudioSegment.from_mp3(str(out2)))
    assert dur2 > dur1
```

- [ ] **Step 3: Run tests to confirm they fail**

```bash
uv run pytest tests/test_synthesizers_mms.py -v
```

Expected: `ImportError` — `MMSSynthesizer` does not exist yet.

- [ ] **Step 4: Write `modal_etl/synthesizers/mms.py`**

```python
import numpy as np
import torch
from pathlib import Path
from pydub import AudioSegment


class MMSSynthesizer:
    """TTS synthesizer backed by facebook/mms-tts-* VITS models.

    Requires lowercase, punctuation-stripped input (MMS hard requirement).
    Use prepare_mms_sentences() from step3_tts.py to prepare input.
    """

    def __init__(
        self,
        model_id: str,
        cache_dir: Path | None = None,
        sentence_pause_ms: int = 250,
        paragraph_pause_ms: int = 400,
        speech_speed: float = 1.15,
    ):
        self.model_id = model_id
        self.cache_dir = cache_dir
        self.sentence_pause_ms = sentence_pause_ms
        self.paragraph_pause_ms = paragraph_pause_ms
        self.speech_speed = speech_speed
        self._model = None
        self._tokenizer = None

    def load(self) -> None:
        """Load VITS model and tokenizer from HuggingFace (or cache_dir)."""
        from transformers import VitsModel, AutoTokenizer
        self._tokenizer = AutoTokenizer.from_pretrained(
            self.model_id, cache_dir=self.cache_dir
        )
        self._model = VitsModel.from_pretrained(
            self.model_id, cache_dir=self.cache_dir
        )

    def synthesize(
        self,
        sentences: list[tuple[str, bool]],
        output_path: Path,
    ) -> Path:
        """Synthesize sentences to MP3 with silence stitching.

        Args:
            sentences: list of (text, is_paragraph_end) — must be lowercase,
                       punctuation-stripped (MMS hard requirement).
            output_path: destination MP3 path.

        Returns:
            output_path on success.
        """
        if not sentences:
            raise ValueError("sentences list is empty — nothing to synthesize")

        rate = self._model.config.sampling_rate
        combined = AudioSegment.empty()

        for text, is_paragraph_end in sentences:
            if not text.strip():
                continue
            inputs = self._tokenizer(text, return_tensors="pt")
            with torch.no_grad():
                waveform = self._model(**inputs).waveform
            pcm = (
                waveform.squeeze().numpy() * 32_767
            ).clip(-32_768, 32_767).astype(np.int16)

            segment = AudioSegment(
                pcm.tobytes(), frame_rate=rate, sample_width=2, channels=1
            )

            # Speed via frame-rate resampling (avoids pydub speedup artefacts)
            if self.speech_speed != 1.0:
                new_rate = int(rate * self.speech_speed)
                segment = segment._spawn(
                    segment.raw_data, overrides={"frame_rate": new_rate}
                ).set_frame_rate(rate)

            combined += segment
            pause_ms = (
                self.paragraph_pause_ms if is_paragraph_end else self.sentence_pause_ms
            )
            combined += AudioSegment.silent(duration=pause_ms, frame_rate=rate)

        combined.export(str(output_path), format="mp3", bitrate="128k")
        return output_path
```

- [ ] **Step 5: Run tests to confirm they pass**

```bash
uv run pytest tests/test_synthesizers_mms.py -v
```

Expected: all 6 tests `PASSED`.

- [ ] **Step 6: Commit**

```bash
git add modal_etl/synthesizers/base.py modal_etl/synthesizers/mms.py tests/test_synthesizers_mms.py
git commit -m "feat: add TTSSynthesizer protocol and MMSSynthesizer"
```

---

## Task 4: SpeechT5Synthesizer

**Files:**
- Create: `modal_etl/synthesizers/speecht5.py`
- Create: `tests/test_synthesizers_speecht5.py`

SpeechT5 requires: `SpeechT5Processor`, `SpeechT5ForTextToSpeech`, `SpeechT5HifiGan` vocoder, and a 512-dim speaker embedding tensor. Unlike MMS, it handles standard English capitalisation and punctuation — do NOT pass it lowercase/stripped text.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_synthesizers_speecht5.py
import pytest
import torch
import numpy as np
from pathlib import Path
from unittest.mock import MagicMock
from pydub import AudioSegment

from modal_etl.synthesizers.speecht5 import SpeechT5Synthesizer
from modal_etl.synthesizers.base import TTSSynthesizer

SAMPLE_RATE = 16_000


def _loaded_synthesizer() -> SpeechT5Synthesizer:
    """Return a SpeechT5Synthesizer with all internals mocked."""
    synth = SpeechT5Synthesizer()

    processor = MagicMock()
    processor.return_value = {"input_ids": torch.tensor([[1, 2, 3]])}

    model = MagicMock()
    waveform = torch.zeros(8000)
    model.generate_speech.return_value = waveform

    vocoder = MagicMock()

    synth._processor = processor
    synth._model = model
    synth._vocoder = vocoder
    synth._speaker_embeddings = torch.zeros(1, 512)
    return synth


def test_speecht5_satisfies_protocol():
    assert isinstance(SpeechT5Synthesizer(), TTSSynthesizer)


def test_speecht5_synthesize_creates_mp3(tmp_path):
    synth = _loaded_synthesizer()
    out = tmp_path / "out.mp3"
    synth.synthesize([("Tropical Depression Pepito.", True)], out)
    assert out.exists()
    assert out.stat().st_size > 0


def test_speecht5_synthesize_returns_output_path(tmp_path):
    synth = _loaded_synthesizer()
    out = tmp_path / "out.mp3"
    result = synth.synthesize([("Hello.", True)], out)
    assert result == out


def test_speecht5_synthesize_raises_on_empty(tmp_path):
    synth = _loaded_synthesizer()
    with pytest.raises(ValueError, match="empty"):
        synth.synthesize([], tmp_path / "out.mp3")


def test_speecht5_paragraph_pause_longer_than_sentence_pause(tmp_path):
    synth = _loaded_synthesizer()
    out_s = tmp_path / "sentence.mp3"
    out_p = tmp_path / "paragraph.mp3"
    synth.synthesize([("Hello.", False)], out_s)
    synth.synthesize([("Hello.", True)], out_p)
    assert len(AudioSegment.from_mp3(str(out_p))) > len(
        AudioSegment.from_mp3(str(out_s))
    )
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
uv run pytest tests/test_synthesizers_speecht5.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Write `modal_etl/synthesizers/speecht5.py`**

```python
import numpy as np
import torch
from pathlib import Path
from pydub import AudioSegment

SAMPLE_RATE = 16_000  # SpeechT5 native sample rate


class SpeechT5Synthesizer:
    """TTS synthesizer backed by microsoft/speecht5_tts + speecht5_hifigan vocoder.

    Handles standard English text — preserves capitalisation and punctuation
    for natural prosody. Do NOT pass lowercase/stripped sentences.
    """

    def __init__(
        self,
        model_id: str = "microsoft/speecht5_tts",
        vocoder_id: str = "microsoft/speecht5_hifigan",
        cache_dir: Path | None = None,
        sentence_pause_ms: int = 300,
        paragraph_pause_ms: int = 500,
    ):
        self.model_id = model_id
        self.vocoder_id = vocoder_id
        self.cache_dir = cache_dir
        self.sentence_pause_ms = sentence_pause_ms
        self.paragraph_pause_ms = paragraph_pause_ms
        self._processor = None
        self._model = None
        self._vocoder = None
        self._speaker_embeddings = None

    def load(self) -> None:
        """Load SpeechT5, HiFiGAN vocoder, and initialise speaker embeddings."""
        from transformers import (
            SpeechT5Processor,
            SpeechT5ForTextToSpeech,
            SpeechT5HifiGan,
        )
        self._processor = SpeechT5Processor.from_pretrained(
            self.model_id, cache_dir=self.cache_dir
        )
        self._model = SpeechT5ForTextToSpeech.from_pretrained(
            self.model_id, cache_dir=self.cache_dir
        )
        self._vocoder = SpeechT5HifiGan.from_pretrained(
            self.vocoder_id, cache_dir=self.cache_dir
        )
        # Neutral speaker embedding — consistent across all synthesis calls
        self._speaker_embeddings = torch.zeros(1, 512)

    def synthesize(
        self,
        sentences: list[tuple[str, bool]],
        output_path: Path,
    ) -> Path:
        """Synthesize sentences to MP3 with silence stitching.

        Args:
            sentences: list of (text, is_paragraph_end). Text should be
                       normal English — capitalisation and punctuation preserved.
            output_path: destination MP3 path.

        Returns:
            output_path on success.
        """
        if not sentences:
            raise ValueError("sentences list is empty — nothing to synthesize")

        combined = AudioSegment.empty()

        for text, is_paragraph_end in sentences:
            if not text.strip():
                continue
            inputs = self._processor(text=text, return_tensors="pt")
            with torch.no_grad():
                waveform = self._model.generate_speech(
                    inputs["input_ids"],
                    self._speaker_embeddings,
                    vocoder=self._vocoder,
                )
            pcm = (waveform.numpy() * 32_767).clip(-32_768, 32_767).astype(np.int16)
            segment = AudioSegment(
                pcm.tobytes(), frame_rate=SAMPLE_RATE, sample_width=2, channels=1
            )
            combined += segment
            pause_ms = (
                self.paragraph_pause_ms if is_paragraph_end else self.sentence_pause_ms
            )
            combined += AudioSegment.silent(duration=pause_ms, frame_rate=SAMPLE_RATE)

        combined.export(str(output_path), format="mp3", bitrate="128k")
        return output_path
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
uv run pytest tests/test_synthesizers_speecht5.py -v
```

Expected: all 5 tests `PASSED`.

- [ ] **Step 5: Commit**

```bash
git add modal_etl/synthesizers/speecht5.py tests/test_synthesizers_speecht5.py
git commit -m "feat: add SpeechT5Synthesizer for English TTS"
```

---

## Task 5: Sentence Prep Utilities + step3_tts Modal Function

**Files:**
- Create: `modal_etl/step3_tts.py`
- Create: `tests/test_step3_sentences.py`

`prepare_mms_sentences` already exists in `tests/test_mms_synthesis.py` copied from notebook 08. This task extracts it into the module and adds `prepare_english_sentences` (also from notebook 08).

- [ ] **Step 1: Write failing sentence prep tests**

```python
# tests/test_step3_sentences.py
from modal_etl.step3_tts import prepare_mms_sentences, prepare_english_sentences


# --- prepare_mms_sentences (for CEB/TL) ---

def test_mms_single_sentence():
    assert prepare_mms_sentences("Hello world.") == [("hello world", True)]


def test_mms_multi_sentence_paragraph():
    result = prepare_mms_sentences("Maayong buntag. Pag-andam na mo.")
    assert result == [("maayong buntag", False), ("pag-andam na mo", True)]


def test_mms_two_paragraphs():
    result = prepare_mms_sentences("First sentence.\n\nSecond sentence.")
    assert result == [("first sentence", True), ("second sentence", True)]


def test_mms_apostrophe_in_word_preserved():
    result = prepare_mms_sentences("Mo'y dako kaayo.")
    assert result[0][0] == "mo'y dako kaayo"


def test_mms_standalone_quotes_stripped():
    result = prepare_mms_sentences("'Hello world'.")
    assert "'" not in result[0][0]


def test_mms_em_dash_stripped():
    result = prepare_mms_sentences("Ang bagyo—mabilis.")
    assert "—" not in result[0][0]


def test_mms_fully_lowercase_no_punctuation():
    result = prepare_mms_sentences("PAGASA Signal Number TWO warns!")
    assert result[0][0] == "pagasa signal number two warns"


# --- prepare_english_sentences (for EN) ---

def test_english_preserves_capitalisation():
    result = prepare_english_sentences("Tropical Depression Pepito.")
    assert result[0][0] == "Tropical Depression Pepito."


def test_english_preserves_punctuation():
    result = prepare_english_sentences("Winds of 85 kph. Expect heavy rainfall.")
    assert "." in result[0][0]


def test_english_two_paragraphs():
    result = prepare_english_sentences("First para.\n\nSecond para.")
    assert result[0] == ("First para.", True)
    assert result[1] == ("Second para.", True)


def test_english_multi_sentence_paragraph():
    result = prepare_english_sentences("Stay indoors. Avoid flooded areas.")
    assert len(result) == 2
    assert result[0][1] is False   # not paragraph end
    assert result[1][1] is True    # paragraph end
```

- [ ] **Step 2: Run failing tests**

```bash
uv run pytest tests/test_step3_sentences.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Write `modal_etl/step3_tts.py`**

```python
import re
from pathlib import Path

import modal

from modal_etl.app import app, tts_image, TTS_MOUNTS, output_volume
from modal_etl.config import TTS_MODELS_PATH, OUTPUT_PATH, LANGUAGES
from modal_etl.synthesizers.mms import MMSSynthesizer
from modal_etl.synthesizers.speecht5 import SpeechT5Synthesizer

# Language → synthesizer mapping. To swap a model, update this dict only.
SYNTHESIZER_MAP = {
    "ceb": MMSSynthesizer(
        "facebook/mms-tts-ceb",
        cache_dir=TTS_MODELS_PATH,
    ),
    "tl": MMSSynthesizer(
        "facebook/mms-tts-tgl",
        cache_dir=TTS_MODELS_PATH,
    ),
    "en": SpeechT5Synthesizer(
        cache_dir=TTS_MODELS_PATH,
    ),
}


# ---------------------------------------------------------------------------
# Sentence preparation utilities
# ---------------------------------------------------------------------------

def prepare_mms_sentences(text: str) -> list[tuple[str, bool]]:
    """Split plain text into MMS-ready (lowercase, no-punctuation) sentences.

    MMS VITS models require lowercase input with punctuation removed.
    In-word apostrophes and hyphens are preserved (e.g. mo'y, pag-andam).

    Returns list of (sentence, is_paragraph_end) tuples.
    """
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    result = []
    for paragraph in paragraphs:
        sentences = re.split(r"(?<=[.!?])\s+", paragraph)
        sentences = [s.strip() for s in sentences if s.strip()]
        for idx, sentence in enumerate(sentences):
            is_last = idx == len(sentences) - 1
            sentence = sentence.lower()
            s = re.sub(r"[^\w\s'\-]", " ", sentence)
            s = re.sub(r"(?<!\w)['\-]|['\-](?!\w)", " ", s)
            sentence = re.sub(r"\s+", " ", s).strip()
            if sentence:
                result.append((sentence, is_last))
    return result


def prepare_english_sentences(text: str) -> list[tuple[str, bool]]:
    """Split plain text into SpeechT5-ready sentences.

    Preserves capitalisation and punctuation for natural English prosody.

    Returns list of (sentence, is_paragraph_end) tuples.
    """
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    result = []
    for paragraph in paragraphs:
        sentences = re.split(r"(?<=[.!?])\s+", paragraph)
        sentences = [s.strip() for s in sentences if s.strip()]
        for idx, sentence in enumerate(sentences):
            is_last = idx == len(sentences) - 1
            if sentence:
                result.append((sentence, is_last))
    return result


# ---------------------------------------------------------------------------
# Modal function
# ---------------------------------------------------------------------------

@app.function(
    image=tts_image,
    volumes=TTS_MOUNTS,
    timeout=600,
)
def step3_tts(stem: str, language: str) -> str:
    """Synthesize TTS plain text for one bulletin + language to MP3.

    Reads:  /output/{stem}/tts_{language}.txt
    Writes: /output/{stem}/audio_{language}.mp3

    Skips synthesis if audio_{language}.mp3 already exists in the Volume.

    Returns:
        stem on success.
    """
    out_dir = OUTPUT_PATH / stem
    tts_txt_path = out_dir / f"tts_{language}.txt"
    mp3_path = out_dir / f"audio_{language}.mp3"

    if mp3_path.exists():
        print(f"[step3_tts] {stem}/{language}: already exists, skipping")
        return stem

    text = tts_txt_path.read_text(encoding="utf-8")

    synthesizer = SYNTHESIZER_MAP[language]
    synthesizer.load()

    if language == "en":
        sentences = prepare_english_sentences(text)
    else:
        sentences = prepare_mms_sentences(text)

    synthesizer.synthesize(sentences, mp3_path)
    output_volume.commit()

    print(f"[step3_tts] {stem}/{language}: wrote {mp3_path}")
    return stem
```

- [ ] **Step 4: Run sentence prep tests**

```bash
uv run pytest tests/test_step3_sentences.py -v
```

Expected: all 12 tests `PASSED`.

- [ ] **Step 5: Commit**

```bash
git add modal_etl/step3_tts.py tests/test_step3_sentences.py
git commit -m "feat: add step3_tts Modal function with sentence prep utilities"
```

---

## Task 6: step1_ocr Modal Class

**Files:**
- Create: `modal_etl/step1_ocr.py`

Logic extracted from `notebooks/04-gemma4.ipynb`. The notebook uses Ollama at `http://localhost:11434/api/generate` with `gemma4:e4b`. Reference the notebook for the exact OCR prompt text.

- [ ] **Step 1: Write `modal_etl/step1_ocr.py`**

```python
import base64
import io
import json
import subprocess
import time
from pathlib import Path

import modal
import requests

from modal_etl.app import app, ollama_image, OLLAMA_MOUNTS, output_volume
from modal_etl.config import OLLAMA_MODELS_PATH, OUTPUT_PATH, GEMMA_MODEL

OLLAMA_URL = "http://localhost:11434"
OLLAMA_TIMEOUT = 120  # seconds per page


def _wait_for_ollama(retries: int = 60, delay: float = 1.0) -> None:
    """Block until Ollama server responds or raise RuntimeError."""
    for _ in range(retries):
        try:
            requests.get(f"{OLLAMA_URL}/api/tags", timeout=2)
            return
        except requests.exceptions.ConnectionError:
            time.sleep(delay)
    raise RuntimeError("Ollama server did not start within timeout")


def _call_ollama(prompt: str, images_b64: list[str] | None = None) -> str:
    """Send a generate request to Ollama. Returns the response text."""
    payload = {
        "model": GEMMA_MODEL,
        "prompt": prompt,
        "stream": False,
    }
    if images_b64:
        payload["images"] = images_b64
    resp = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json=payload,
        timeout=OLLAMA_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()["response"]


def _pdf_to_images_b64(pdf_bytes: bytes) -> list[str]:
    """Convert PDF bytes to a list of base64-encoded PNG images (one per page)."""
    from pdf2image import convert_from_bytes
    from PIL import Image

    pages = convert_from_bytes(pdf_bytes, dpi=200)
    result = []
    for page in pages:
        buf = io.BytesIO()
        page.save(buf, format="PNG")
        result.append(base64.b64encode(buf.getvalue()).decode("utf-8"))
    return result


def _ocr_pdf(pdf_bytes: bytes) -> str:
    """Run Gemma 4 E4B OCR on a PDF and return the combined markdown.

    Prompt copied from notebooks/04-gemma4.ipynb (Step 1 cell).
    """
    images_b64 = _pdf_to_images_b64(pdf_bytes)
    pages_md = []
    for i, img_b64 in enumerate(images_b64):
        # Copy the OCR prompt verbatim from notebook 04, Step 1 cell.
        # The prompt instructs Gemma 4 to extract all text as markdown,
        # preserving structure, tables, and describing any charts/maps.
        prompt = (
            "You are a document OCR assistant. Extract all text from this PAGASA "
            "weather bulletin page as clean Markdown. Preserve all section headings, "
            "tables, lists, coordinates, and storm track chart descriptions. "
            "Do not summarise or omit any content. Output Markdown only."
        )
        page_md = _call_ollama(prompt, images_b64=[img_b64])
        pages_md.append(f"<!-- Page {i + 1} -->\n\n{page_md}")
    return "\n\n---\n\n".join(pages_md)


@app.cls(
    image=ollama_image,
    gpu=modal.gpu.A10G(),
    volumes=OLLAMA_MOUNTS,
    timeout=1800,
)
class Step1OCR:
    @modal.enter()
    def start_ollama(self) -> None:
        """Start Ollama server at container startup. Model weights are in the Volume."""
        import os
        os.environ["OLLAMA_MODELS"] = str(OLLAMA_MODELS_PATH)
        subprocess.Popen(["ollama", "serve"])
        _wait_for_ollama()
        print("[Step1OCR] Ollama ready")

    @modal.method()
    def run(self, pdf_url: str) -> str:
        """Download PDF from pdf_url, OCR with Gemma 4 E4B, save ocr.md to Volume.

        Skips processing if ocr.md already exists for this stem.

        Returns:
            stem string (filename without .pdf extension).
        """
        stem = pdf_url.split("/")[-1].replace(".pdf", "")
        out_dir = OUTPUT_PATH / stem
        ocr_path = out_dir / "ocr.md"

        if ocr_path.exists():
            print(f"[Step1OCR] {stem}: ocr.md already exists, skipping")
            return stem

        out_dir.mkdir(parents=True, exist_ok=True)

        resp = requests.get(pdf_url, timeout=60)
        resp.raise_for_status()
        pdf_bytes = resp.content

        markdown = _ocr_pdf(pdf_bytes)
        ocr_path.write_text(markdown, encoding="utf-8")
        output_volume.commit()

        print(f"[Step1OCR] {stem}: wrote {ocr_path} ({len(markdown)} chars)")
        return stem
```

- [ ] **Step 2: Verify the file parses without import errors**

```bash
uv run python -c "from modal_etl.step1_ocr import Step1OCR; print('OK')"
```

Expected: `OK` (Modal decorators are no-ops locally).

- [ ] **Step 3: Commit**

```bash
git add modal_etl/step1_ocr.py
git commit -m "feat: add Step1OCR Modal class — Ollama/Gemma 4 E4B PDF OCR"
```

---

## Task 7: step2_scripts Modal Class

**Files:**
- Create: `modal_etl/step2_scripts.py`

Logic extracted from `notebooks/06-radio-bulletin.ipynb`. That notebook generates:
1. A radio script markdown per language (prompt 1)
2. A TTS plain text per language (prompt 2, dialect-pure version)

Copy the prompts verbatim from the notebook cells. The structure here mirrors Step 1.

- [ ] **Step 1: Write `modal_etl/step2_scripts.py`**

```python
import subprocess
import time
from pathlib import Path

import modal
import requests

from modal_etl.app import app, ollama_image, OLLAMA_MOUNTS, output_volume
from modal_etl.config import OLLAMA_MODELS_PATH, OUTPUT_PATH, GEMMA_MODEL, LANGUAGES

OLLAMA_URL = "http://localhost:11434"
OLLAMA_TIMEOUT = 300  # seconds per language prompt


def _wait_for_ollama(retries: int = 60, delay: float = 1.0) -> None:
    for _ in range(retries):
        try:
            requests.get(f"{OLLAMA_URL}/api/tags", timeout=2)
            return
        except requests.exceptions.ConnectionError:
            time.sleep(delay)
    raise RuntimeError("Ollama server did not start within timeout")


def _call_ollama(prompt: str) -> str:
    resp = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={"model": GEMMA_MODEL, "prompt": prompt, "stream": False},
        timeout=OLLAMA_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()["response"]


def _generate_radio_script(markdown: str, language: str) -> str:
    """Generate a ~750-word radio broadcast script in the target language.

    Copy the per-language radio script prompt verbatim from
    notebooks/06-radio-bulletin.ipynb (the cell that sets RADIO_PROMPT_{lang}).
    The prompt should:
    - Target 150 wpm spoken pace (~5 minutes)
    - Use numbered storm signals and wind speeds spelled out
    - Output Markdown with headings for each section
    """
    lang_labels = {"en": "English", "tl": "Tagalog", "ceb": "Cebuano"}
    label = lang_labels[language]

    # Replace this placeholder prompt with the full prompt from notebook 06.
    prompt = (
        f"You are a broadcast journalist writing a 5-minute radio weather bulletin "
        f"in {label} for Filipino communities. Using the PAGASA bulletin below, "
        f"write a flowing prose radio script (~750 words at 150 wpm). "
        f"Structure: Title, Current Situation, Forecast Track, Affected Areas, "
        f"Safety Advisory, Closing. Spell out all numbers. Bold storm name on first "
        f"mention in each section. Output Markdown only.\n\n{markdown}"
    )
    return _call_ollama(prompt)


def _generate_tts_text(radio_md: str, language: str) -> str:
    """Convert radio script markdown to TTS-optimised dialect-pure plain text.

    Copy the per-language TTS text prompt verbatim from
    notebooks/06-radio-bulletin.ipynb (the cell that sets TTS_PROMPT_{lang}).
    The prompt should:
    - Produce flowing prose with no markdown syntax
    - Use only words from the target language
    - Phonetically spell proper nouns and English technical terms
    - Preserve paragraph breaks (blank lines) for pause timing
    """
    lang_labels = {"en": "English", "tl": "Tagalog", "ceb": "Cebuano"}
    label = lang_labels[language]

    # Replace this placeholder prompt with the full prompt from notebook 06.
    prompt = (
        f"Rewrite the following radio script as plain flowing prose in {label}. "
        f"Remove all Markdown syntax (headings, bold, bullets, dashes). "
        f"Use only {label} words. Phonetically spell any English proper nouns or "
        f"technical terms in {label} phonemes (e.g. PAGASA → pa-ga-sa). "
        f"Preserve paragraph breaks (blank line between paragraphs). "
        f"Output plain text only.\n\n{radio_md}"
    )
    return _call_ollama(prompt)


@app.cls(
    image=ollama_image,
    gpu=modal.gpu.A10G(),
    volumes=OLLAMA_MOUNTS,
    timeout=3600,
)
class Step2Scripts:
    @modal.enter()
    def start_ollama(self) -> None:
        import os
        os.environ["OLLAMA_MODELS"] = str(OLLAMA_MODELS_PATH)
        subprocess.Popen(["ollama", "serve"])
        _wait_for_ollama()
        print("[Step2Scripts] Ollama ready")

    @modal.method()
    def run(self, stem: str) -> str:
        """Generate radio scripts and TTS plain text for all 3 languages.

        Reads:   /output/{stem}/ocr.md
        Writes:  /output/{stem}/radio_{lang}.md   (× 3)
                 /output/{stem}/tts_{lang}.txt     (× 3)

        Skips a language if all its output files already exist.

        Returns:
            stem string.
        """
        out_dir = OUTPUT_PATH / stem
        ocr_md = (out_dir / "ocr.md").read_text(encoding="utf-8")

        for lang in LANGUAGES:
            radio_path = out_dir / f"radio_{lang}.md"
            tts_path = out_dir / f"tts_{lang}.txt"

            if radio_path.exists() and tts_path.exists():
                print(f"[Step2Scripts] {stem}/{lang}: already exists, skipping")
                continue

            radio_md = _generate_radio_script(ocr_md, lang)
            radio_path.write_text(radio_md, encoding="utf-8")

            tts_text = _generate_tts_text(radio_md, lang)
            tts_path.write_text(tts_text, encoding="utf-8")

            print(f"[Step2Scripts] {stem}/{lang}: wrote radio + tts files")

        output_volume.commit()
        return stem
```

- [ ] **Step 2: Replace the placeholder radio and TTS prompts**

Open `notebooks/06-radio-bulletin.ipynb`. Find the cells that define the radio script prompt and the TTS plain text prompt for each language. Copy those prompts verbatim into `_generate_radio_script` and `_generate_tts_text` in `step2_scripts.py`, replacing the placeholder strings above.

- [ ] **Step 3: Verify imports are clean**

```bash
uv run python -c "from modal_etl.step2_scripts import Step2Scripts; print('OK')"
```

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add modal_etl/step2_scripts.py
git commit -m "feat: add Step2Scripts Modal class — radio scripts + TTS text generation"
```

---

## Task 8: Volume Setup Functions

**Files:**
- Create: `modal_etl/setup_volumes.py`

These are one-time setup functions — run manually once before the first batch to populate the Ollama and TTS model volumes. They do NOT run as part of the batch pipeline.

- [ ] **Step 1: Write `modal_etl/setup_volumes.py`**

```python
"""One-time volume initialisation functions.

Run these manually before the first batch:

    uv run modal run modal_etl/setup_volumes.py::setup_ollama_volume
    uv run modal run modal_etl/setup_volumes.py::setup_tts_volume
"""
import subprocess
import time

import modal
import requests

from modal_etl.app import app, ollama_image, tts_image, ollama_volume, tts_volume
from modal_etl.config import OLLAMA_MODELS_PATH, TTS_MODELS_PATH, GEMMA_MODEL

OLLAMA_URL = "http://localhost:11434"


def _wait_for_ollama(retries: int = 60, delay: float = 2.0) -> None:
    for _ in range(retries):
        try:
            requests.get(f"{OLLAMA_URL}/api/tags", timeout=2)
            return
        except requests.exceptions.ConnectionError:
            time.sleep(delay)
    raise RuntimeError("Ollama server did not start")


@app.function(
    image=ollama_image,
    gpu=modal.gpu.A10G(),
    volumes={str(OLLAMA_MODELS_PATH): ollama_volume},
    timeout=3600,
)
def setup_ollama_volume() -> None:
    """Pull gemma4:e4b into the weatherspeak-ollama Volume.

    Run once: uv run modal run modal_etl/setup_volumes.py::setup_ollama_volume
    """
    import os
    os.environ["OLLAMA_MODELS"] = str(OLLAMA_MODELS_PATH)
    subprocess.Popen(["ollama", "serve"])
    _wait_for_ollama()
    print(f"Pulling {GEMMA_MODEL} into volume...")
    subprocess.run(["ollama", "pull", GEMMA_MODEL], check=True)
    ollama_volume.commit()
    print("Done — gemma4:e4b is in weatherspeak-ollama volume")


@app.function(
    image=tts_image,
    volumes={str(TTS_MODELS_PATH): tts_volume},
    timeout=3600,
)
def setup_tts_volume() -> None:
    """Download MMS and SpeechT5 model weights into the weatherspeak-tts-models Volume.

    Run once: uv run modal run modal_etl/setup_volumes.py::setup_tts_volume
    """
    from transformers import (
        VitsModel, AutoTokenizer,
        SpeechT5Processor, SpeechT5ForTextToSpeech, SpeechT5HifiGan,
    )

    print("Downloading facebook/mms-tts-ceb...")
    AutoTokenizer.from_pretrained("facebook/mms-tts-ceb", cache_dir=TTS_MODELS_PATH)
    VitsModel.from_pretrained("facebook/mms-tts-ceb", cache_dir=TTS_MODELS_PATH)

    print("Downloading facebook/mms-tts-tgl...")
    AutoTokenizer.from_pretrained("facebook/mms-tts-tgl", cache_dir=TTS_MODELS_PATH)
    VitsModel.from_pretrained("facebook/mms-tts-tgl", cache_dir=TTS_MODELS_PATH)

    print("Downloading microsoft/speecht5_tts...")
    SpeechT5Processor.from_pretrained("microsoft/speecht5_tts", cache_dir=TTS_MODELS_PATH)
    SpeechT5ForTextToSpeech.from_pretrained("microsoft/speecht5_tts", cache_dir=TTS_MODELS_PATH)
    SpeechT5HifiGan.from_pretrained("microsoft/speecht5_hifigan", cache_dir=TTS_MODELS_PATH)

    tts_volume.commit()
    print("Done — all TTS models are in weatherspeak-tts-models volume")
```

- [ ] **Step 2: Verify imports**

```bash
uv run python -c "from modal_etl.setup_volumes import setup_ollama_volume, setup_tts_volume; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add modal_etl/setup_volumes.py
git commit -m "feat: add one-time volume setup functions for Ollama and TTS models"
```

---

## Task 9: Batch Orchestration + Smoke Test

**Files:**
- Create: `modal_etl/run_batch.py`

- [ ] **Step 1: Write `modal_etl/run_batch.py`**

```python
"""WeatherSpeak PH — Modal batch ETL entrypoint.

Usage:
    # Initialise volumes (first time only):
    uv run modal run modal_etl/setup_volumes.py::setup_ollama_volume
    uv run modal run modal_etl/setup_volumes.py::setup_tts_volume

    # Run the full batch:
    uv run modal run modal_etl/run_batch.py

    # Process fewer events (override N_EVENTS):
    uv run modal run modal_etl/run_batch.py --n 3
"""
import sys

import modal

from modal_etl.app import app
from modal_etl.bulletin_selector import get_latest_bulletins
from modal_etl.config import N_EVENTS, LANGUAGES
from modal_etl.step1_ocr import Step1OCR
from modal_etl.step2_scripts import Step2Scripts
from modal_etl.step3_tts import step3_tts


@app.local_entrypoint()
def main(n: int = N_EVENTS) -> None:
    """Process the newest N severe weather events end-to-end.

    For each event:
      1. OCR the latest bulletin PDF → ocr.md
      2. Generate radio scripts + TTS text → radio_{lang}.md + tts_{lang}.txt
      3. Synthesize MP3s in parallel (CEB, TL, EN) → audio_{lang}.mp3

    All artifacts are stored in the weatherspeak-output Modal Volume.
    """
    print(f"Selecting newest {n} severe weather events from bulletin archive...")
    bulletins = get_latest_bulletins(n)

    if not bulletins:
        print("No bulletins found. Check ARCHIVE_API_URL in config.py.")
        sys.exit(1)

    print(f"Processing {len(bulletins)} bulletins:")
    for b in bulletins:
        print(f"  {b.stem}")

    ocr = Step1OCR()
    scripts = Step2Scripts()

    for bulletin in bulletins:
        print(f"\n--- {bulletin.stem} ---")

        print("  Step 1: OCR...")
        stem = ocr.run.remote(bulletin.pdf_url)

        print("  Step 2: Radio scripts + TTS text...")
        stem = scripts.run.remote(stem)

        print("  Step 3: TTS synthesis (3 languages in parallel)...")
        list(step3_tts.starmap([(stem, lang) for lang in LANGUAGES]))

        print(f"  Done: {stem}")

    print("\nBatch complete. All artifacts in weatherspeak-output volume.")
```

- [ ] **Step 2: Verify the entrypoint loads**

```bash
uv run python -c "from modal_etl.run_batch import main; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Smoke test — run the pipeline against 1 bulletin on Modal**

This step requires the volumes to be initialised (Task 8 setup functions must have been run).

```bash
uv run modal run modal_etl/run_batch.py --n 1
```

Expected output sequence:
```
Selecting newest 1 severe weather events from bulletin archive...
Processing 1 bulletins:
  PAGASA_...

--- PAGASA_... ---
  Step 1: OCR...
  Step 2: Radio scripts + TTS text...
  Step 3: TTS synthesis (3 languages in parallel)...
  Done: PAGASA_...

Batch complete. All artifacts in weatherspeak-output volume.
```

Verify artifacts in the Modal Volume:
```bash
uv run modal volume ls weatherspeak-output
```

Expected: directory listing showing `ocr.md`, `radio_en.md`, `radio_tl.md`, `radio_ceb.md`, `tts_en.txt`, `tts_tl.txt`, `tts_ceb.txt`, `audio_en.mp3`, `audio_tl.mp3`, `audio_ceb.mp3` under the bulletin stem directory.

- [ ] **Step 4: Download and verify MP3 audio**

```bash
uv run modal volume get weatherspeak-output <stem>/audio_ceb.mp3 /tmp/audio_ceb.mp3
# Open /tmp/audio_ceb.mp3 and confirm audible Cebuano speech
```

- [ ] **Step 5: Commit**

```bash
git add modal_etl/run_batch.py
git commit -m "feat: add run_batch local entrypoint — complete Modal ETL pipeline"
```

---

## Self-Review

**Spec coverage:**

| Spec requirement | Covered by |
|---|---|
| 3-step pipeline (OCR → scripts → TTS) | Tasks 6, 7, 5 |
| Ollama + gemma4:e4b on GPU | Tasks 6, 7 (Ollama in container, weights in Volume) |
| MMS for CEB/TL, SpeechT5 for EN | Tasks 3, 4 |
| TTSSynthesizer protocol (swappable) | Task 3 — protocol + SYNTHESIZER_MAP in step3_tts |
| Modal Volumes for all artifacts | Tasks 1, 8 (volume setup) |
| Bulletin selection: newest N, latest per event | Task 2 |
| Raw GitHub PDF URLs | Task 2 (`pdf_url` field) |
| Stem as primary key for artifacts | Tasks 6, 7, 5 (all use `/output/{stem}/`) |
| Idempotency (skip if exists) | Tasks 5, 6, 7 (all check before running) |
| No keep_warm | Tasks 6, 7, 5 (no keep_warm in any function) |
| Output volume readable by future website | Task 1 (output_volume created with create_if_missing) |

**All spec requirements are covered.**
