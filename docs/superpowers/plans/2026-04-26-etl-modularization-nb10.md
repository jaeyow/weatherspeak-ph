# ETL Modularization + Notebook 10 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract reusable pure-Python business logic from `modal_etl/step*.py` into `modal_etl/core/`, refactor the step files into thin Modal wrappers, and create notebook 10 (`notebooks/10-etl-e2e.ipynb`) that runs the full PDF→MP3 pipeline locally using those core modules.

**Architecture:** New `modal_etl/core/` sub-package holds four modules (`ollama.py`, `ocr.py`, `scripts.py`, `tts.py`) with no Modal imports. Each existing step file shrinks to ~10 lines: start Ollama if needed → call `core.*:run_step*` → commit volume. The notebook imports directly from `modal_etl.core.*`.

**Tech Stack:** Python 3.12, Ollama HTTP API (`http://localhost:11434`), Gemma 4 E4B, Facebook MMS VITS, Coqui XTTS v2, pdf2image, uv, pytest.

---

## File Map

| Action | Path | Responsibility |
|--------|------|---------------|
| Create | `modal_etl/core/__init__.py` | Empty package marker |
| Create | `modal_etl/core/ollama.py` | Shared Ollama HTTP helpers |
| Create | `modal_etl/core/ocr.py` | PDF→OCR markdown + metadata JSON |
| Create | `modal_etl/core/scripts.py` | Radio scripts + TTS text generation |
| Create | `modal_etl/core/tts.py` | Sentence prep + MP3 synthesis runner |
| Create | `tests/test_core_ollama.py` | Unit tests for ollama helpers |
| Create | `tests/test_core_ocr.py` | Unit tests for run_step1 skip logic |
| Create | `tests/test_core_scripts.py` | Unit tests for run_step2 + _clean_ocr |
| Create | `tests/test_core_tts.py` | Unit tests for run_step3 skip/error logic |
| Create | `notebooks/10-etl-e2e.ipynb` | End-to-end local pipeline notebook |
| Modify | `modal_etl/step1_ocr.py` | Thin Modal wrapper → calls `core/ocr.py` |
| Modify | `modal_etl/step2_scripts.py` | Thin Modal wrapper → calls `core/scripts.py` |
| Modify | `modal_etl/step3_tts.py` | Thin Modal wrapper → calls `core/tts.py` |
| Modify | `tests/test_step2_format_metadata.py` | Update import path |
| Modify | `tests/test_step3_sentences.py` | Update import path |
| Modify | `tests/test_schema_validation.py` | Update import path |

---

## Task 1: Create `modal_etl/core/` package with `ollama.py`

**Files:**
- Create: `modal_etl/core/__init__.py`
- Create: `modal_etl/core/ollama.py`
- Create: `tests/test_core_ollama.py`

- [ ] **Step 1.1: Write the failing tests**

Create `tests/test_core_ollama.py`:

```python
"""Tests for modal_etl/core/ollama.py."""
import pytest
from unittest.mock import patch, MagicMock
from modal_etl.core.ollama import wait_for_ollama, call_ollama_generate, call_ollama_chat


def test_wait_for_ollama_raises_when_server_unreachable():
    """wait_for_ollama raises RuntimeError after exhausting retries."""
    import requests
    with patch("modal_etl.core.ollama.requests.get", side_effect=requests.exceptions.ConnectionError):
        with patch("modal_etl.core.ollama.time.sleep"):
            with pytest.raises(RuntimeError, match="did not respond"):
                wait_for_ollama("http://localhost:11434", retries=2, delay=0.0)


def test_wait_for_ollama_returns_when_server_ready():
    """wait_for_ollama returns normally when server responds."""
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    with patch("modal_etl.core.ollama.requests.get", return_value=mock_resp):
        wait_for_ollama("http://localhost:11434", retries=1, delay=0.0)


def test_call_ollama_generate_sends_correct_payload():
    """call_ollama_generate POSTs to /api/generate with expected fields."""
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"response": "test output"}
    with patch("modal_etl.core.ollama.requests.post", return_value=mock_resp) as mock_post:
        result = call_ollama_generate(
            url="http://localhost:11434",
            model="gemma4:e4b",
            prompt="test prompt",
            system="test system",
        )
    assert result == "test output"
    payload = mock_post.call_args.kwargs["json"]
    assert payload["model"] == "gemma4:e4b"
    assert payload["prompt"] == "test prompt"
    assert payload["system"] == "test system"
    assert payload["stream"] is False


def test_call_ollama_generate_includes_images_when_provided():
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"response": "ok"}
    with patch("modal_etl.core.ollama.requests.post", return_value=mock_resp) as mock_post:
        call_ollama_generate(
            url="http://localhost:11434",
            model="gemma4:e4b",
            prompt="describe image",
            images_b64=["abc123"],
        )
    payload = mock_post.call_args.kwargs["json"]
    assert payload["images"] == ["abc123"]


def test_call_ollama_chat_strips_think_blocks():
    """call_ollama_chat removes <think>...</think> from the response."""
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "message": {"content": "<think>internal reasoning</think>The actual answer."}
    }
    with patch("modal_etl.core.ollama.requests.post", return_value=mock_resp):
        result = call_ollama_chat(
            url="http://localhost:11434",
            model="gemma4:e4b",
            system="you are helpful",
            user="what is 2+2",
        )
    assert result == "The actual answer."
    assert "<think>" not in result


def test_call_ollama_chat_sends_chat_messages():
    """call_ollama_chat POSTs to /api/chat with system + user messages."""
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"message": {"content": "response"}}
    with patch("modal_etl.core.ollama.requests.post", return_value=mock_resp) as mock_post:
        call_ollama_chat(
            url="http://localhost:11434",
            model="gemma4:e4b",
            system="sys",
            user="usr",
        )
    payload = mock_post.call_args.kwargs["json"]
    assert payload["messages"][0] == {"role": "system", "content": "sys"}
    assert payload["messages"][1] == {"role": "user", "content": "usr"}
```

- [ ] **Step 1.2: Run tests to verify they fail**

```bash
uv run pytest tests/test_core_ollama.py -v
```
Expected: `ModuleNotFoundError: No module named 'modal_etl.core'`

- [ ] **Step 1.3: Create the package and implement `ollama.py`**

Create `modal_etl/core/__init__.py` (empty):
```python
```

Create `modal_etl/core/ollama.py`:
```python
import re
import time

import requests


def wait_for_ollama(url: str, retries: int = 60, delay: float = 2.0) -> None:
    """Block until Ollama responds on /api/tags or raise RuntimeError."""
    for _ in range(retries):
        try:
            requests.get(f"{url}/api/tags", timeout=5)
            return
        except (requests.exceptions.ConnectionError, requests.exceptions.ReadTimeout):
            time.sleep(delay)
    raise RuntimeError(f"Ollama at {url} did not respond within timeout")


def call_ollama_generate(
    url: str,
    model: str,
    prompt: str,
    system: str | None = None,
    images_b64: list[str] | None = None,
    fmt: dict | None = None,
    timeout: int = 600,
) -> str:
    """POST /api/generate and return the response text."""
    payload: dict = {"model": model, "prompt": prompt, "stream": False}
    if system:
        payload["system"] = system
    if images_b64:
        payload["images"] = images_b64
    if fmt:
        payload["format"] = fmt
    resp = requests.post(f"{url}/api/generate", json=payload, timeout=timeout)
    resp.raise_for_status()
    return resp.json()["response"]


def call_ollama_chat(
    url: str,
    model: str,
    system: str,
    user: str,
    timeout: int = 300,
) -> str:
    """POST /api/chat and return the assistant message, stripped of <think> blocks."""
    resp = requests.post(
        f"{url}/api/chat",
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
        },
        timeout=timeout,
    )
    resp.raise_for_status()
    content = resp.json()["message"]["content"].strip()
    content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
    return content
```

- [ ] **Step 1.4: Run tests to verify they pass**

```bash
uv run pytest tests/test_core_ollama.py -v
```
Expected: all 6 tests PASS.

- [ ] **Step 1.5: Update `step1_ocr.py` to use core ollama helpers**

In `modal_etl/step1_ocr.py`, replace the module-level `_wait_for_ollama` and `_call_ollama` functions with imports from core, and update call sites.

Replace the import block and the two function definitions (lines 1–175) so the file begins:

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
from modal_etl.core.ollama import wait_for_ollama, call_ollama_generate

OLLAMA_URL = "http://localhost:11434"
OLLAMA_TIMEOUT = 600
```

Remove the `_wait_for_ollama` function definition (lines 144–152) and the `_call_ollama` function definition (lines 155–175).

Update all calls to `_call_ollama(...)` in `_ocr_pdf`, `_find_chart_page`, and `_generate_metadata` to use `call_ollama_generate(url=OLLAMA_URL, model=GEMMA_MODEL, ...)`.

Update `_ocr_pdf`:
```python
def _ocr_pdf(pages) -> str:
    pages_md = []
    for i, page in enumerate(pages):
        img_b64 = _page_to_b64(page)
        page_md = call_ollama_generate(
            url=OLLAMA_URL,
            model=GEMMA_MODEL,
            prompt=_OCR_USER,
            system=_OCR_SYSTEM,
            images_b64=[img_b64],
            timeout=OLLAMA_TIMEOUT,
        )
        pages_md.append(f"<!-- Page {i + 1} -->\n\n{page_md}")
    return "\n\n---\n\n".join(pages_md)
```

Update `_find_chart_page`:
```python
def _find_chart_page(pages) -> int:
    all_b64 = [_page_to_b64(p) for p in pages]
    prompt = (
        f"This PAGASA weather bulletin has {len(pages)} pages (0-indexed: "
        f"0 to {len(pages) - 1}). "
        "Which page contains the storm track map or weather disturbance chart? "
        "Reply with a single integer — the 0-based page index only. No explanation."
    )
    response = call_ollama_generate(
        url=OLLAMA_URL,
        model=GEMMA_MODEL,
        prompt=prompt,
        images_b64=all_b64,
        timeout=OLLAMA_TIMEOUT,
    ).strip()
    try:
        idx = int(response.split()[0])
        return max(0, min(idx, len(pages) - 1))
    except (ValueError, IndexError):
        return len(pages) - 1
```

Update `_generate_metadata`:
```python
def _generate_metadata(markdown: str) -> dict:
    prompt = (
        "Here is the extracted text from a PAGASA bulletin:\n\n"
        f"{markdown}\n\n"
        "Convert this into the structured JSON schema."
    )
    raw = call_ollama_generate(
        url=OLLAMA_URL,
        model=GEMMA_MODEL,
        prompt=prompt,
        system=_METADATA_SYSTEM,
        fmt=PAGASA_JSON_SCHEMA,
        timeout=OLLAMA_TIMEOUT,
    )
    return json.loads(raw)
```

Update `start_ollama` in the class to call `wait_for_ollama(OLLAMA_URL)` instead of `_wait_for_ollama()`.

- [ ] **Step 1.6: Update `step2_scripts.py` to use core ollama helpers**

In `modal_etl/step2_scripts.py`, replace the module-level `_wait_for_ollama` and `_call_ollama_chat` definitions with imports from core.

Replace the import block so it includes:
```python
from modal_etl.core.ollama import wait_for_ollama, call_ollama_chat as _core_chat
```

Remove the `_wait_for_ollama` function (lines 518–525) and the `_call_ollama_chat` function (lines 543–561).

Update `_generate_radio_script`, `_generate_tts_text`, `_cleanup_english_words`, `_cleanup_numbers` to call `_core_chat(url=OLLAMA_URL, model=GEMMA_MODEL, system=..., user=...)` instead of the old `_call_ollama_chat(system=..., user=...)`.

Update `_generate_radio_script`:
```python
def _generate_radio_script(ocr_md: str, language: str, metadata: dict | None = None) -> str:
    if metadata is not None:
        bulletin_data = (
            "=== KEY FACTS (use these for accuracy — do not confuse fields) ===\n"
            f"{_format_metadata_for_prompt(metadata)}\n"
            "=== FULL BULLETIN TEXT (use for completeness) ===\n"
            f"{ocr_md}"
        )
    else:
        bulletin_data = ocr_md
    p = _RADIO_PROMPTS[language]
    return _core_chat(
        url=OLLAMA_URL,
        model=GEMMA_MODEL,
        system=p["system"],
        user=p["user"].format(bulletin_data=bulletin_data),
    )
```

Update `_generate_tts_text`:
```python
def _generate_tts_text(radio_md: str, language: str) -> str:
    p = _TTS_PROMPTS[language]
    text = _core_chat(
        url=OLLAMA_URL,
        model=GEMMA_MODEL,
        system=p["system"],
        user=p["user"].format(markdown=radio_md),
    )
    return apply_phonetics(text, language)
```

Update `_cleanup_english_words`:
```python
def _cleanup_english_words(text: str, language: str) -> str:
    if language not in _CLEANUP_PROMPTS:
        return text
    p = _CLEANUP_PROMPTS[language]
    return _core_chat(
        url=OLLAMA_URL,
        model=GEMMA_MODEL,
        system=p["system"],
        user=p["user"].format(text=text),
    )
```

Update `_cleanup_numbers`:
```python
def _cleanup_numbers(text: str, language: str) -> str:
    if language not in _NUMBER_CLEANUP_PROMPTS:
        return text
    p = _NUMBER_CLEANUP_PROMPTS[language]
    return _core_chat(
        url=OLLAMA_URL,
        model=GEMMA_MODEL,
        system=p["system"],
        user=p["user"].format(text=text),
    )
```

Update `step2_scripts` function body to call `wait_for_ollama(OLLAMA_URL)` instead of `_wait_for_ollama()`.

- [ ] **Step 1.7: Run all existing tests to verify no regressions**

```bash
uv run pytest tests/ -v
```
Expected: all existing tests PASS (they still import from `step1_ocr` and `step2_scripts` which now delegate to core).

- [ ] **Step 1.8: Commit**

```bash
git add modal_etl/core/__init__.py modal_etl/core/ollama.py tests/test_core_ollama.py modal_etl/step1_ocr.py modal_etl/step2_scripts.py
git commit -m "feat: extract shared Ollama HTTP helpers into modal_etl/core/ollama.py"
```

---

## Task 2: Create `modal_etl/core/ocr.py` and refactor `step1_ocr.py`

**Files:**
- Create: `modal_etl/core/ocr.py`
- Create: `tests/test_core_ocr.py`
- Modify: `modal_etl/step1_ocr.py` (full replacement with thin wrapper)
- Modify: `tests/test_schema_validation.py` (update import)

- [ ] **Step 2.1: Write the failing tests**

Create `tests/test_core_ocr.py`:

```python
"""Tests for modal_etl/core/ocr.py — skip logic and path handling only (no Ollama/PIL)."""
import json
import pytest
from pathlib import Path
from modal_etl.core.ocr import run_step1, PAGASA_JSON_SCHEMA


def _write_all_step1_outputs(stem_dir: Path) -> None:
    (stem_dir / "ocr.md").write_text("# OCR content", encoding="utf-8")
    (stem_dir / "chart.png").write_bytes(b"fakepng")
    (stem_dir / "metadata.json").write_text('{"bulletin_type": "TCA"}', encoding="utf-8")


def test_run_step1_skips_when_all_outputs_exist(tmp_path):
    """run_step1 returns stem_dir immediately when all outputs exist and force=False."""
    stem = "PAGASA_TEST"
    pdf_path = tmp_path / f"{stem}.pdf"
    pdf_path.write_bytes(b"fake pdf")
    stem_dir = tmp_path / stem
    stem_dir.mkdir()
    _write_all_step1_outputs(stem_dir)

    result = run_step1(pdf_path, tmp_path, force=False)

    assert result == stem_dir


def test_run_step1_uses_stem_override(tmp_path):
    """run_step1 uses the stem parameter instead of pdf_path.stem when provided."""
    pdf_path = tmp_path / "irrelevant_name.pdf"
    pdf_path.write_bytes(b"fake pdf")
    custom_stem = "PAGASA_22-TC02_Basyang_TCA#01"
    stem_dir = tmp_path / custom_stem
    stem_dir.mkdir()
    _write_all_step1_outputs(stem_dir)

    result = run_step1(pdf_path, tmp_path, stem=custom_stem, force=False)

    assert result == stem_dir


def test_run_step1_force_reruns_even_when_outputs_exist(tmp_path, monkeypatch):
    """run_step1 with force=True calls _ocr_pdf even when outputs already exist."""
    stem = "PAGASA_TEST"
    pdf_path = tmp_path / f"{stem}.pdf"
    pdf_path.write_bytes(b"fake pdf")
    stem_dir = tmp_path / stem
    stem_dir.mkdir()
    _write_all_step1_outputs(stem_dir)

    called = []
    monkeypatch.setattr("modal_etl.core.ocr._pdf_to_pil_pages", lambda b, dpi=200: [])
    monkeypatch.setattr("modal_etl.core.ocr._ocr_pdf", lambda pages, url, model: (called.append(1), "# forced")[1])
    monkeypatch.setattr("modal_etl.core.ocr._find_chart_page", lambda pages, url, model: 0)
    monkeypatch.setattr("modal_etl.core.ocr._generate_metadata", lambda md, url, model: {"bulletin_type": "TCA", "storm": {"name": "T", "category": "Typhoon"}, "issuance": {}, "current_position": {}, "intensity": {}, "movement": {}, "forecast_positions": [], "affected_areas": {}, "storm_track_map": {}, "confidence": 1.0})

    class FakePage:
        def save(self, path, format): pass

    monkeypatch.setattr("modal_etl.core.ocr._pdf_to_pil_pages", lambda b, dpi=200: [FakePage()])

    run_step1(pdf_path, tmp_path, force=True)
    assert len(called) == 1


def test_pagasa_json_schema_has_required_fields():
    """PAGASA_JSON_SCHEMA defines all required top-level fields."""
    required = PAGASA_JSON_SCHEMA["required"]
    for field in ["bulletin_type", "storm", "issuance", "current_position",
                  "intensity", "movement", "forecast_positions", "affected_areas",
                  "storm_track_map", "confidence"]:
        assert field in required
```

- [ ] **Step 2.2: Run tests to verify they fail**

```bash
uv run pytest tests/test_core_ocr.py -v
```
Expected: `ImportError: cannot import name 'run_step1' from 'modal_etl.core.ocr'`

- [ ] **Step 2.3: Create `modal_etl/core/ocr.py`**

```python
import base64
import io
import json
from pathlib import Path

from modal_etl.core.ollama import call_ollama_generate

OLLAMA_TIMEOUT = 600

PAGASA_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "bulletin_type": {"type": "string", "enum": ["SWB", "TCA", "TCB", "other"]},
        "bulletin_number": {"type": ["integer", "null"]},
        "storm": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "international_name": {"type": ["string", "null"]},
                "category": {
                    "type": "string",
                    "enum": [
                        "Tropical Depression",
                        "Tropical Storm",
                        "Severe Tropical Storm",
                        "Typhoon",
                        "Super Typhoon",
                    ],
                },
                "wind_signal": {"type": ["integer", "null"]},
            },
            "required": ["name", "category"],
        },
        "issuance": {
            "type": "object",
            "properties": {
                "datetime": {"type": ["string", "null"]},
                "valid_until": {"type": ["string", "null"]},
            },
        },
        "current_position": {
            "type": "object",
            "properties": {
                "latitude": {"type": ["number", "null"]},
                "longitude": {"type": ["number", "null"]},
                "reference": {"type": ["string", "null"]},
                "as_of": {"type": ["string", "null"]},
            },
        },
        "intensity": {
            "type": "object",
            "properties": {
                "max_sustained_winds_kph": {"type": ["integer", "null"]},
                "gusts_kph": {"type": ["integer", "null"]},
            },
        },
        "movement": {
            "type": "object",
            "properties": {
                "direction": {"type": ["string", "null"]},
                "speed_kph": {"type": ["integer", "null"]},
            },
        },
        "forecast_positions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "hour": {"type": "integer"},
                    "label": {"type": "string"},
                    "latitude": {"type": ["number", "null"]},
                    "longitude": {"type": ["number", "null"]},
                    "reference": {"type": ["string", "null"]},
                },
                "required": ["hour", "label"],
            },
        },
        "affected_areas": {
            "type": "object",
            "properties": {
                "signal_1": {"type": "array", "items": {"type": "string"}},
                "signal_2": {"type": "array", "items": {"type": "string"}},
                "signal_3": {"type": "array", "items": {"type": "string"}},
                "signal_4": {"type": "array", "items": {"type": "string"}},
                "signal_5": {"type": "array", "items": {"type": "string"}},
                "rainfall_warning": {"type": "array", "items": {"type": "string"}},
                "coastal_waters": {"type": ["string", "null"]},
            },
        },
        "storm_track_map": {
            "type": "object",
            "properties": {
                "current_position_shown": {"type": "boolean"},
                "forecast_track_shown": {"type": "boolean"},
                "description": {"type": ["string", "null"]},
            },
        },
        "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
    },
    "required": [
        "bulletin_type",
        "storm",
        "issuance",
        "current_position",
        "intensity",
        "movement",
        "forecast_positions",
        "affected_areas",
        "storm_track_map",
        "confidence",
    ],
}

_OCR_SYSTEM = (
    "You are an expert OCR assistant specialising in Philippine government weather documents.\n\n"
    "Your task is to extract ALL text from the provided PAGASA typhoon bulletin image as accurately as possible.\n\n"
    "OUTPUT RULES:\n"
    "- Output clean Markdown that preserves the document's structure (headings, tables, lists, sections).\n"
    "- Include every piece of visible text: headers, body, tables, footnotes, labels, legends, logos.\n"
    "- For the storm track map/chart, describe what you see: storm position, forecast track, affected regions, symbols and legend items.\n"
    "- Do NOT summarise, paraphrase, or omit any content.\n"
    "- Do NOT add commentary or explanation outside the document content."
)

_OCR_USER = "Extract all text and describe the storm track map from this PAGASA typhoon bulletin image."

_METADATA_SYSTEM = (
    "You are PAGASAParseAI, an expert at converting extracted PAGASA typhoon bulletin text into structured JSON.\n\n"
    "Extract only the fields listed in the schema. Do not include full_text or any free-form text dump.\n\n"
    "CRITICAL RULES:\n"
    "- Output ONLY the JSON object. No preamble, no markdown fences, no explanation.\n"
    "- If a field cannot be determined, use null or an empty array. Never hallucinate.\n"
    "- forecast_positions must include every position shown (24h, 48h, 72h, 96h, 120h)."
)


def _pdf_to_pil_pages(pdf_bytes: bytes, dpi: int = 200):
    """Convert PDF bytes to a list of PIL Image objects (one per page)."""
    from pdf2image import convert_from_bytes
    return convert_from_bytes(pdf_bytes, dpi=dpi)


def _page_to_b64(pil_image) -> str:
    """Encode a PIL image as a base64 PNG string."""
    buf = io.BytesIO()
    pil_image.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def _ocr_pdf(pages, ollama_url: str, model: str) -> str:
    """Run Gemma 4 E4B OCR on each page and return combined markdown."""
    pages_md = []
    for i, page in enumerate(pages):
        img_b64 = _page_to_b64(page)
        page_md = call_ollama_generate(
            url=ollama_url,
            model=model,
            prompt=_OCR_USER,
            system=_OCR_SYSTEM,
            images_b64=[img_b64],
            timeout=OLLAMA_TIMEOUT,
        )
        pages_md.append(f"<!-- Page {i + 1} -->\n\n{page_md}")
    return "\n\n---\n\n".join(pages_md)


def _find_chart_page(pages, ollama_url: str, model: str) -> int:
    """Ask Gemma 4 which page (0-indexed) contains the storm track map."""
    all_b64 = [_page_to_b64(p) for p in pages]
    prompt = (
        f"This PAGASA weather bulletin has {len(pages)} pages (0-indexed: "
        f"0 to {len(pages) - 1}). "
        "Which page contains the storm track map or weather disturbance chart? "
        "Reply with a single integer — the 0-based page index only. No explanation."
    )
    response = call_ollama_generate(
        url=ollama_url,
        model=model,
        prompt=prompt,
        images_b64=all_b64,
        timeout=OLLAMA_TIMEOUT,
    ).strip()
    try:
        idx = int(response.split()[0])
        return max(0, min(idx, len(pages) - 1))
    except (ValueError, IndexError):
        return len(pages) - 1


def _generate_metadata(markdown: str, ollama_url: str, model: str) -> dict:
    """Extract structured bulletin data from OCR markdown using constrained decoding."""
    prompt = (
        "Here is the extracted text from a PAGASA bulletin:\n\n"
        f"{markdown}\n\n"
        "Convert this into the structured JSON schema."
    )
    raw = call_ollama_generate(
        url=ollama_url,
        model=model,
        prompt=prompt,
        system=_METADATA_SYSTEM,
        fmt=PAGASA_JSON_SCHEMA,
        timeout=OLLAMA_TIMEOUT,
    )
    return json.loads(raw)


def run_step1(
    pdf_path: Path,
    output_dir: Path,
    ollama_url: str = "http://localhost:11434",
    model: str = "gemma4:e4b",
    force: bool = False,
    stem: str | None = None,
) -> Path:
    """Run OCR on pdf_path and write ocr.md, chart.png, metadata.json to output_dir/{stem}/.

    Args:
        pdf_path:   Local path to the PDF file.
        output_dir: Base output directory. Artefacts written to output_dir/{stem}/.
        ollama_url: Ollama server URL (already running).
        model:      Ollama model tag.
        force:      Re-run even if all output files already exist.
        stem:       Override for the bulletin stem; defaults to pdf_path.stem.

    Returns:
        Path to the stem-scoped output directory (output_dir/{stem}/).
    """
    stem = stem or pdf_path.stem
    out_dir = output_dir / stem
    ocr_path = out_dir / "ocr.md"
    chart_path = out_dir / "chart.png"
    metadata_path = out_dir / "metadata.json"

    if ocr_path.exists() and chart_path.exists() and metadata_path.exists() and not force:
        print(f"[run_step1] {stem}: all outputs exist, skipping")
        return out_dir

    out_dir.mkdir(parents=True, exist_ok=True)
    pdf_bytes = pdf_path.read_bytes()
    pages = _pdf_to_pil_pages(pdf_bytes)

    if not ocr_path.exists() or force:
        markdown = _ocr_pdf(pages, ollama_url, model)
        ocr_path.write_text(markdown, encoding="utf-8")
        print(f"[run_step1] {stem}: wrote ocr.md ({len(markdown)} chars)")
    else:
        markdown = ocr_path.read_text(encoding="utf-8")

    if not chart_path.exists() or force:
        chart_idx = _find_chart_page(pages, ollama_url, model)
        pages[chart_idx].save(str(chart_path), format="PNG")
        print(f"[run_step1] {stem}: saved chart.png (page {chart_idx})")

    if not metadata_path.exists() or force:
        metadata = _generate_metadata(markdown, ollama_url, model)
        metadata_path.write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"[run_step1] {stem}: wrote metadata.json")

    return out_dir
```

- [ ] **Step 2.4: Run tests to verify they pass**

```bash
uv run pytest tests/test_core_ocr.py -v
```
Expected: all 4 tests PASS.

- [ ] **Step 2.5: Replace `step1_ocr.py` with a thin Modal wrapper**

Completely replace `modal_etl/step1_ocr.py` with:

```python
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import unquote

import modal
import requests

from modal_etl.app import app, ollama_image, OLLAMA_MOUNTS, output_volume
from modal_etl.config import OLLAMA_MODELS_PATH, OUTPUT_PATH, GEMMA_MODEL
from modal_etl.core.ocr import run_step1
from modal_etl.core.ollama import wait_for_ollama

OLLAMA_URL = "http://localhost:11434"


@app.cls(
    image=ollama_image,
    gpu="A10G",
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
        wait_for_ollama(OLLAMA_URL)
        print("[Step1OCR] Ollama ready")

    @modal.method()
    def run(self, pdf_url: str, force: bool = False) -> str:
        """Download PDF from URL and run step 1 OCR pipeline.

        Returns:
            stem string (filename without .pdf extension).
        """
        stem = unquote(pdf_url.split("/")[-1].replace(".pdf", ""))
        resp = requests.get(pdf_url, timeout=60)
        resp.raise_for_status()
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(resp.content)
            pdf_path = Path(f.name)
        run_step1(pdf_path, OUTPUT_PATH, OLLAMA_URL, GEMMA_MODEL, force, stem=stem)
        output_volume.commit()
        return stem
```

- [ ] **Step 2.6: Update `tests/test_schema_validation.py` import**

Change line:
```python
from modal_etl.step1_ocr import PAGASA_JSON_SCHEMA
```
to:
```python
from modal_etl.core.ocr import PAGASA_JSON_SCHEMA
```

- [ ] **Step 2.7: Run all tests to verify no regressions**

```bash
uv run pytest tests/ -v
```
Expected: all tests PASS.

- [ ] **Step 2.8: Commit**

```bash
git add modal_etl/core/ocr.py tests/test_core_ocr.py modal_etl/step1_ocr.py tests/test_schema_validation.py
git commit -m "feat: extract OCR logic into modal_etl/core/ocr.py, step1_ocr becomes thin wrapper"
```

---

## Task 3: Create `modal_etl/core/scripts.py` and refactor `step2_scripts.py`

**Files:**
- Create: `modal_etl/core/scripts.py`
- Create: `tests/test_core_scripts.py`
- Modify: `modal_etl/step2_scripts.py` (full replacement with thin wrapper)
- Modify: `tests/test_step2_format_metadata.py` (update import)

- [ ] **Step 3.1: Update import in `tests/test_step2_format_metadata.py`**

Change line:
```python
from modal_etl.step2_scripts import _format_metadata_for_prompt
```
to:
```python
from modal_etl.core.scripts import _format_metadata_for_prompt
```

- [ ] **Step 3.2: Write additional failing tests**

Create `tests/test_core_scripts.py`:

```python
"""Tests for modal_etl/core/scripts.py — skip logic and _clean_ocr."""
import pytest
from pathlib import Path
from modal_etl.core.scripts import run_step2, _clean_ocr


def _write_step2_outputs(stem_dir: Path, lang: str) -> None:
    (stem_dir / f"radio_{lang}.md").write_text("# Radio script", encoding="utf-8")
    (stem_dir / f"tts_{lang}.txt").write_text("Plain text.", encoding="utf-8")


def test_run_step2_skips_when_outputs_exist(tmp_path):
    """run_step2 returns radio_path immediately when both outputs exist and force=False."""
    stem = "PAGASA_TEST"
    stem_dir = tmp_path / stem
    stem_dir.mkdir()
    (stem_dir / "ocr.md").write_text("# OCR", encoding="utf-8")
    (stem_dir / "metadata.json").write_text('{"bulletin_type": "TCA", "storm": {"name": "T", "category": "Typhoon"}}', encoding="utf-8")
    _write_step2_outputs(stem_dir, "en")

    result = run_step2(stem, "en", tmp_path, force=False)

    assert result == stem_dir / "radio_en.md"


def test_run_step2_raises_when_ocr_missing(tmp_path):
    """run_step2 raises FileNotFoundError when ocr.md does not exist."""
    stem = "PAGASA_TEST"
    stem_dir = tmp_path / stem
    stem_dir.mkdir()

    with pytest.raises(FileNotFoundError, match="ocr.md"):
        run_step2(stem, "en", tmp_path, force=False)


def test_clean_ocr_removes_bracket_placeholder_lines():
    """_clean_ocr strips lines that are entirely a [BRACKET LABEL]."""
    raw = "Normal text.\n[HEADER BLOCK]\nMore normal text."
    result = _clean_ocr(raw)
    assert "[HEADER BLOCK]" not in result
    assert "Normal text." in result
    assert "More normal text." in result


def test_clean_ocr_collapses_extra_blank_lines():
    """_clean_ocr collapses runs of 3+ blank lines to a single blank line."""
    raw = "Para one.\n\n\n\nPara two."
    result = _clean_ocr(raw)
    assert "\n\n\n" not in result


def test_clean_ocr_preserves_inline_brackets():
    """_clean_ocr does NOT strip [brackets] that appear mid-line."""
    raw = "Signal [1] areas include Catanduanes."
    result = _clean_ocr(raw)
    assert "Signal [1] areas include Catanduanes." in result
```

- [ ] **Step 3.3: Run tests to verify they fail**

```bash
uv run pytest tests/test_step2_format_metadata.py tests/test_core_scripts.py -v
```
Expected: `ImportError: cannot import name '_format_metadata_for_prompt' from 'modal_etl.core.scripts'`

- [ ] **Step 3.4: Create `modal_etl/core/scripts.py`**

This file holds all the prompts, helpers, and `run_step2`. Copy the prompt dicts and helper functions from `step2_scripts.py`, updating each helper that made Ollama calls to accept `ollama_url` and `model` parameters and use `call_ollama_chat` from `core/ollama.py`.

```python
import json
import re
from pathlib import Path

from modal_etl.core.ollama import call_ollama_chat
from modal_etl.phonetics import apply_phonetics

# ---------------------------------------------------------------------------
# Prompts — copied verbatim from step2_scripts.py
# ---------------------------------------------------------------------------

_RADIO_PROMPTS = {
    "en": {
        "system": (
            "You are converting a PAGASA typhoon bulletin into a short weather announcement in English "
            "that will be displayed on a website and read aloud as audio.\n\n"
            "PURPOSE: This will be read by Filipinos who may not understand technical English — "
            "farmers, fisherfolk, and rural communities who need to know if they are in danger and what to do. "
            "Every word must earn its place. There is no room for anything that does not help them act.\n\n"
            "PRIORITY ORDER — pack these in, in this order, within 200 words:\n"
            "  1. Storm name and current category (what is it)\n"
            "  2. Where it is now and where it is headed (location + track)\n"
            "  3. Which areas are affected and at what Signal level (who is in danger)\n"
            "  4. What people must do — evacuate, stay indoors, avoid the coast (action)\n"
            "  5. When the next update is (so they know to listen again)\n\n"
            "STYLE:\n"
            "- Write as if explaining to a neighbour — conversational, simple, direct\n"
            "- No broadcaster language, no formal sign-offs, no station IDs\n"
            "- Short sentences. Common words. Cut anything that does not add critical information.\n"
            "- Use digits for numbers (e.g. '25 kilometres per hour', 'Signal 2')\n"
            "- Write place names naturally as they are spelled (e.g. Catanduanes, Visayas, Mindanao)\n"
            "- DO NOT add information that is not in the original bulletin\n\n"
            "FORMATTING: Plain flowing prose only. No headings, no bullet points, no bold, no markdown. "
            "Paragraph breaks (blank lines) between ideas.\n\n"
            "LENGTH: No more than 200 words. Be concise — a life may depend on someone understanding this clearly."
        ),
        "user": (
            "Convert this PAGASA weather bulletin data into a plain conversational English announcement.\n\n"
            "{bulletin_data}\n\n"
            "Write the announcement now. Pack in all critical information — storm, location, track, "
            "affected areas with Signal levels, what to do, next update time. "
            "No more than 200 words. No headings, no markdown. Write place names naturally."
        ),
    },
    "tl": {
        "system": (
            "Ikaw ay nagsusulat ng maikling pahayag tungkol sa isang malakas na bagyo sa Tagalog "
            "na ipapakita sa isang website at babasahin nang malakas bilang audio.\n\n"
            "LAYUNIN: Mababasa at maririnig ito ng mga Pilipinong maaaring hindi nakakaintindi ng Ingles — "
            "mga magsasaka, mangingisda, at mga komunidad na kailangang malaman kung sila ay nasa panganib at ano ang gagawin. "
            "Bawat salita ay mahalaga. Walang lugar para sa anumang hindi nakakatulong sa kanilang kumilos.\n\n"
            "PAGKAKASUNOD NG IMPORMASYON — ilagay ang lahat ng ito, sa pagkakasunod na ito, sa loob ng 200 salita:\n"
            "  1. Pangalan ng bagyo at kasalukuyang kategorya (ano ito)\n"
            "  2. Nasaan ito ngayon at saan ito pupunta (lokasyon + landas)\n"
            "  3. Aling mga lugar ang apektado at anong Signal level (sino ang nasa panganib)\n"
            "  4. Ano ang dapat gawin — lumikas, manatiling nasa loob, umiwas sa baybayin (aksyon)\n"
            "  5. Kailan ang susunod na update (para malaman nila kung kailan muling makikinig)\n\n"
            "ESTILO — PURO TAGALOG, WALANG INGLES:\n"
            "- Magsulat na parang nagkukwento ka sa isang kapitbahay — simple, natural, walang paligoy-ligoy\n"
            "- BAWAL ang mga salitang Ingles maliban sa mga pangalan ng tao at lugar (hal. Pepito, Catanduanes, Luzon)\n"
            "- Gamitin ang pang-araw-araw na Tagalog — hindi pormal, hindi opisyal, hindi balita sa TV\n"
            "- Isulat ang mga teknikal na termino sa natural na Tagalog na katumbas:\n"
            "    bagyo (typhoon), bagyong malakas (severe tropical storm), agos ng hangin (wind speed),\n"
            "    signal bilang isa/dalawa/tatlo, mababang presyon, malakas na alon, lumikas, baybaying-dagat\n"
            "- Maikling pangungusap. Madaling salita. Alisin ang anumang hindi nagdadagdag ng kritikal na impormasyon.\n"
            "- Gamitin ang mga digit para sa mga numero (hal. 25 kilometro bawat oras, Signal 2)\n"
            "- HUWAG magdagdag ng impormasyon na wala sa orihinal na bulletin\n\n"
            "FORMATTING: Natural na daloy ng prosa. Walang headings, walang bullets, walang bold, walang markdown. "
            "Blank lines sa pagitan ng mga talata.\n\n"
            "HABA: Hindi hihigit sa 200 salita. Maging maigsi — maaaring ang buhay ng isang tao ay nakasalalay sa malinaw na pag-unawa nito."
        ),
        "user": (
            "I-convert ang datos ng PAGASA bulletin na ito sa maikling pahayag sa Tagalog.\n\n"
            "{bulletin_data}\n\n"
            "Isulat ang pahayag ngayon. Ilagay ang lahat ng kritikal na impormasyon — bagyo, lokasyon, landas, "
            "mga apektadong lugar na may Signal level, ano ang gagawin, oras ng susunod na update. "
            "Hindi hihigit sa 200 salita. Puro Tagalog. Walang headings, walang markdown."
        ),
    },
    "ceb": {
        "system": (
            "Ikaw nagsulat og mubo nga pahimangno bahin sa usa ka kusog nga bagyo sa Cebuano "
            "nga ipakita sa usa ka website ug basahon sa makusog isip audio.\n\n"
            "KATUYOAN: Mabasa ug madungog kini sa mga Pilipino nga mahimong dili makasabot sa English — "
            "mga mag-uuma, mangingisda, ug mga komunidad nga kinahanglan mahibalo kung sila anaa sa peligro ug unsa ang buhaton. "
            "Ang matag pulong importante. Walay lugar alang sa bisan unsang dili makatulong kanila nga molihok.\n\n"
            "PAGKASUNOD SA IMPORMASYON — ibutang ang tanan niini, sa pagkasunod nga kini, sulod sa 200 ka pulong:\n"
            "  1. Ngalan sa bagyo ug kasamtangang kategorya (unsa kini)\n"
            "  2. Asa kini karon ug asa kini padulong (lokasyon + dalan)\n"
            "  3. Unsang mga lugar ang apektado ug unsang Signal level (kinsa ang anaa sa peligro)\n"
            "  4. Unsa ang buhaton — paglikas, magpabilin sulod, likayi ang baybayon (aksyon)\n"
            "  5. Kanus-a ang sunod nga update (aron mahibalo sila kung kanus-a usab sila mamati)\n\n"
            "ESTILO — PURO CEBUANO, WALAY ENGLISH:\n"
            "- Pagsulat sama sa imong gisulti sa imong silingan — simple, natural, dili komplikado\n"
            "- BAWAL ang mga pulong nga Ingles gawas sa mga pangalan sa tawo ug lugar (hal. Pepito, Catanduanes, Luzon)\n"
            "- Gamita ang inadlaw-adlaw nga Cebuano — dili pormal, dili opisyal, dili balita sa TV\n"
            "- Isulat ang mga teknikal nga termino sa natural nga Cebuano nga katumbas:\n"
            "    bagyo (typhoon), kusog nga bagyo (severe tropical storm), kusog sa hangin (wind speed),\n"
            "    signal numero uno/dos/tres, ubos nga presyon, kusog nga balud, paglikas, baybayon\n"
            "- Mubo nga mga sentence. Sayon nga mga pulong. Kuhaa ang bisan unsang dili nagdugang og kritikal nga impormasyon.\n"
            "- Gamita ang mga digit para sa mga numero (hal. 25 kilometros sa usa ka oras, Signal 2)\n"
            "- AYAW pagdugang og impormasyon nga wala sa orihinal nga bulletin\n\n"
            "FORMATTING: Natural nga daloy sa prosa. Walay headings, walay bullets, walay bold, walay markdown. "
            "Blank lines tali sa mga paragraph.\n\n"
            "GITAS-ON: Dili molapas sa 200 ka pulong. Pagmaiksi — ang kinabuhi sa usa ka tawo mahimong magdepende sa tin-aw nga pagsabot niini."
        ),
        "user": (
            "I-convert ang datos sa PAGASA bulletin nga kini ngadto sa mubo nga pahimangno sa Cebuano.\n\n"
            "{bulletin_data}\n\n"
            "Isulat ang pahimangno karon. Ibutang ang tanan nga kritikal nga impormasyon — bagyo, lokasyon, dalan, "
            "mga apektadong lugar nga adunay Signal level, unsa ang buhaton, oras sa sunod nga update. "
            "Dili molapas sa 200 ka pulong. Puro Cebuano. Walay headings, walay markdown."
        ),
    },
}

_TTS_PROMPTS = {
    "en": {
        "system": (
            "You are converting a PAGASA severe weather announcement into plain text for text-to-speech synthesis.\n\n"
            "AUDIENCE: Filipinos with low literacy, limited education, and no English background. "
            "Keep the language simple. Short sentences. Common words only.\n\n"
            "RULES:\n"
            "- NO markdown: no headings (#), no bullet points (-), no asterisks (*), no bold/italic\n"
            "- NO placeholders. Never write [station name], [insert...], [your location], or anything in brackets.\n"
            "- NO radio show language. No 'Good morning listeners', no sign-offs, no station IDs.\n"
            "- Rewrite as natural flowing prose — paragraph breaks (blank lines) for pausing\n"
            "- Use simple, short words. If the original uses a complex word, use a simpler one.\n"
            "- DO NOT add any information that was not in the original script\n"
            "- Output: plain text only, no markup or formatting characters"
        ),
        "user": (
            "Read this markdown weather announcement and rewrite it as TTS-ready plain English text.\n\n"
            "{markdown}\n\n"
            "Write the plain English text now. Simple words. Short sentences. "
            "Paragraph breaks (blank lines) for natural pausing. No markdown. No placeholders."
        ),
    },
    "tl": {
        "system": (
            "Ikaw ay nagko-convert ng PAGASA severe weather announcement sa plain text para sa text-to-speech synthesis.\n\n"
            "AUDIENCE: Mga Pilipinong may mababang literacy, limitadong edukasyon, at walang English background. "
            "Gumamit ng simple na wika. Maikling mga pangungusap. Mga karaniwang salita lamang.\n\n"
            "PINAKAMAHALAGANG PANUNTUNAN:\n"
            "WALANG INGLES. BAWAT salitang Ingles na makikita mo sa script ay DAPAT palitan ng Tagalog o ng phonetically spelled na anyo. "
            "Ang tanging pagbubukod ay mga pangalan ng tao at lugar (hal. 'Pepito', 'Catanduanes', 'Isabela').\n\n"
            "WALANG PLACEHOLDER. Huwag isulat ang [pangalan ng istasyon], [ilagay...], [iyong lokasyon], o anumang nasa brackets.\n\n"
            "WALANG RADIO SHOW NA WIKA. Walang 'Magandang umaga mga tagapakinig', walang sign-offs, walang station IDs.\n\n"
            "MANDATORY NA PHONETIC SPELLINGS — gamitin ang mga ito palagi, hindi ang Ingles:\n"
            "  - Tropical Depression → tro-pi-kal di-pre-syon\n"
            "  - Tropical Storm → tro-pi-kal storm\n"
            "  - Severe Tropical Storm → se-beer tro-pi-kal storm\n"
            "  - Typhoon → tai-pun\n"
            "  - Super Typhoon → su-per tai-pun\n"
            "  - PAGASA / PAG-ASA → pag-asa\n"
            "  - forecast → pore-kast\n"
            "  - advisory → ad-bay-so-ri\n"
            "  - bulletin → bu-le-tin\n"
            "  - warning → wor-ning\n"
            "  - update → ap-deyt\n"
            "  - Signal Number One / Two / Three / Four / Five → sig-nal nam-ber wan / tu / tri / por / payb\n"
            "  - kilometers per hour / kph / km/h → ki-lo-me-tro ba-wat o-ras\n"
            "  - northeast / southeast / northwest / southwest → nor-ist / sow-ist / nor-west / sow-west\n"
            "  - north / south / east → nor / sow / ist\n"
            "  - northern / southern / eastern / western → nor-dern / sow-dern / is-tern / wes-tern\n"
            "  - Low Pressure Area / LPA → mababang presyon\n"
            "PARA SA MGA NUMERO — gamita ang Filipino/Spanish na mga salita:\n"
            "  - 25 km/h → beinte singko ki-lo-me-tro ba-wat o-ras\n"
            "  - 65 km/h → sisenta y singko ki-lo-me-tro ba-wat o-ras\n"
            "  - 95 km/h → nobenta y singko ki-lo-me-tro ba-wat o-ras\n"
            "  - 120 km/h → isang daan at dalawampu ki-lo-me-tro ba-wat o-ras\n"
            "  - 130 km/h → isang daan at tatlumpu ki-lo-me-tro ba-wat o-ras\n"
            "  - 150 km/h → isang daan at limampu ki-lo-me-tro ba-wat o-ras\n"
            "  - 200 km/h → dalawang daan ki-lo-me-tro ba-wat o-ras\n"
            "  - Para sa iba pang numero: 5=singko, 10=diyes, 15=kinse, 20=beinte,\n"
            "    30=treynta, 40=kuwarenta, 50=singkwenta, 60=sisenta,\n"
            "    70=sitenta, 80=otsenta, 90=nobenta, 100=isang daan\n\n"
            "  - hPa → ek-to-pas-kal\n"
            "  - coastal → kos-tal\n"
            "  - landfall → land-pol\n"
            "  - storm surge → storm serj\n"
            "  - flash flood → plash plud\n"
            "  - emergency → i-mer-chen-si\n"
            "  - evacuation → i-bak-yu-ey-syon\n"
            "  - center → sen-ter\n"
            "  - official → o-pi-syal\n"
            "  - Luzon → lu-son\n"
            "  - Visayas → bi-sa-yas\n"
            "  - Mindanao → min-da-naw\n\n"
            "IBA PANG PANUNTUNAN:\n"
            "- WALANG markdown: walang # headings, walang - bullets, walang * bold/italic\n"
            "- Isulat bilang natural na daloy ng prosa na angkop para basahin nang malakas\n"
            "- Panatilihin ang paragraph structure: blank lines sa pagitan ng mga paragraph\n"
            "- HUWAG magdagdag ng anumang texto na wala sa orihinal na script\n"
            "- Output: plain text lamang"
        ),
        "user": (
            "Basahin ang markdown weather announcement na ito at isulat muli ito bilang TTS-ready plain Tagalog text.\n\n"
            "{markdown}\n\n"
            "TANDAAN: Tagalog lamang — WALANG INGLES maliban sa mga pangalan ng tao at lugar. "
            "Gamitin ang phonetically spelled na anyo para sa lahat ng teknikal na termino. "
            "Walang placeholder. Walang radio show na wika. "
            "Paragraph breaks (blank lines) para sa natural na pausing. Walang markdown."
        ),
    },
    "ceb": {
        "system": (
            "Ikaw nagko-convert sa PAGASA severe weather announcement ngadto sa plain text para sa text-to-speech synthesis.\n\n"
            "AUDIENCE: Mga Pilipino nga may ubos nga literacy, limitado nga edukasyon, ug walay English background. "
            "Gamita ang simple nga pinulongan. Mubo nga mga sentence. Komon nga mga pulong lamang.\n\n"
            "PINAKA-IMPORTANTE NGA LAGDA:\n"
            "WALAY ENGLISH. ANG MATAG English word nga imong makita sa script KINAHANGLAN palitan sa Cebuano o sa phonetically spelled nga porma. "
            "Ang bugtong eksepsyon mao ang mga pangalan sa tawo ug lugar (hal. 'Pepito', 'Catanduanes', 'Isabela').\n\n"
            "WALAY PLACEHOLDER. Ayaw isulat ang [ngalan sa istasyon], [ibutang...], [imong lokasyon], o bisan unsa nga anaa sa brackets.\n\n"
            "WALAY RADIO SHOW NGA PULONG. Walay 'Maayong buntag mga tigpaminaw', walay sign-offs, walay station IDs.\n\n"
            "MANDATORY NGA PHONETIC SPELLINGS — gamita kini kanunay, dili ang English:\n"
            "  - Tropical Depression → tro-pi-kal di-pre-syon\n"
            "  - Tropical Storm → tro-pi-kal storm\n"
            "  - Severe Tropical Storm → se-beer tro-pi-kal storm\n"
            "  - Typhoon → tai-pun\n"
            "  - Super Typhoon → su-per tai-pun\n"
            "  - PAGASA / PAG-ASA → pag-asa\n"
            "  - forecast → pore-kast\n"
            "  - advisory → ad-bay-so-ri\n"
            "  - bulletin → bu-le-tin\n"
            "  - warning → wor-ning\n"
            "  - update → ap-deyt\n"
            "  - Signal Number One / Two / Three / Four / Five → sig-nal nam-ber wan / tu / tri / por / payb\n"
            "  - kilometers per hour / kph / km/h → ki-lo-me-tros sa usa ka oras\n"
            "  - northeast / southeast / northwest / southwest → nor-ist / sow-ist / nor-west / sow-west\n"
            "  - north / south / east → nor / sow / ist\n"
            "  - northern / southern / eastern / western → nor-dern / sow-dern / is-tern / wes-tern\n"
            "  - Low Pressure Area / LPA → lo-presyur-erya\n"
            "PARA SA MGA NUMERO — gamita ang Cebuano/Spanish nga mga pulong:\n"
            "  - 25 km/h → baynte singko ki-lo-me-tros sa usa ka oras\n"
            "  - 65 km/h → sisenta y singko ki-lo-me-tros sa usa ka oras\n"
            "  - 95 km/h → nobenta y singko ki-lo-me-tros sa usa ka oras\n"
            "  - 120 km/h → isyento baynte ki-lo-me-tros sa usa ka oras\n"
            "  - 130 km/h → isyento treynta ki-lo-me-tros sa usa ka oras\n"
            "  - 150 km/h → isyento singkwenta ki-lo-me-tros sa usa ka oras\n"
            "  - 200 km/h → dos siyentos ki-lo-me-tros sa usa ka oras\n"
            "  - Para sa ubang numero: 5=singko, 10=diyes, 15=kinse, 20=baynte,\n"
            "    30=treynta, 40=kuwarenta, 50=singkwenta, 60=sisenta,\n"
            "    70=sitenta, 80=otsenta, 90=nobenta, 100=isyento\n\n"
            "  - hPa → ek-to-pas-kal\n"
            "  - coastal → kos-tal\n"
            "  - landfall → land-pol\n"
            "  - storm surge → storm serj\n"
            "  - flash flood → plash plud\n"
            "  - emergency → i-mer-chen-si\n"
            "  - evacuation → i-bak-yu-ey-syon\n"
            "  - center → sen-ter\n"
            "  - official → o-pi-syal\n"
            "  - Luzon → lu-son\n"
            "  - Visayas → bi-sa-yas\n"
            "  - Mindanao → min-da-naw\n\n"
            "UBAN PA NGA MGA LAGDA:\n"
            "- WALAY markdown: walay # headings, walay - bullets, walay * bold/italic\n"
            "- Isulat isip natural nga daloy sa prosa nga angay basahon sa makusog\n"
            "- Pahimusa ang paragraph structure: blank lines tali sa mga paragraph\n"
            "- AYAW pagdugang og bisan unsa nga texto nga wala sa orihinal nga script\n"
            "- Output: plain text lamang"
        ),
        "user": (
            "Basaha kining markdown weather announcement ug isulat kini pag-usab isip TTS-ready plain Cebuano text.\n\n"
            "{markdown}\n\n"
            "HINUMDUMI: Cebuano lamang — WALAY ENGLISH gawas sa mga pangalan sa tawo ug lugar. "
            "Gamita ang phonetically spelled nga porma para sa tanan nga teknikal nga termino. "
            "Walay placeholder. Walay radio show nga pulong. "
            "Paragraph breaks (blank lines) para sa natural nga pausing. Walay markdown."
        ),
    },
}

_CLEANUP_PROMPTS = {
    "tl": {
        "system": (
            "Ikaw ay isang editor ng Tagalog TTS text. Ang iyong trabaho ay hanapin ang mga salitang Ingles "
            "at palitan ang mga ito ng tamang Tagalog o phonetically spelled na anyo.\n\n"
            "PANUNTUNAN:\n"
            "- Hanapin ang LAHAT ng salitang Ingles sa text\n"
            "- Palitan ng Tagalog na katumbas o phonetically spelled na anyo (gamit ang mga gitling)\n"
            "- Mga pangalan ng tao at lugar ay HINDI dapat palitan (hal. Pepito, Catanduanes, Luzon)\n"
            "- Huwag baguhin ang anumang bagay na hindi Ingles\n"
            "- Ibalik ang BUONG text na may mga pagbabago lamang\n"
            "- Walang markdown, walang paliwanag — plain text lamang\n\n"
            "HALIMBAWA NG PAGPAPALIT:\n"
            "  'storm surge' → 'storm serj'\n"
            "  'landfall' → 'land-pol'\n"
            "  'coastal' → 'kos-tal'\n"
            "  'warning' → 'wor-ning'\n"
            "  'advisory' → 'ad-bay-so-ri'\n"
            "  'signal' → 'sig-nal'\n"
            "  'forecast' → 'pore-kast'\n"
            "  'emergency' → 'i-mer-chen-si'\n"
            "  'evacuation' → 'i-bak-yu-ey-syon'"
        ),
        "user": (
            "Suriin ang Tagalog TTS text na ito. Hanapin ang lahat ng salitang Ingles at palitan ng "
            "Tagalog o phonetically spelled na anyo. Ibalik ang buong text na may mga pagbabago.\n\n"
            "{text}"
        ),
    },
    "ceb": {
        "system": (
            "Ikaw usa ka editor sa Cebuano TTS text. Ang imong trabaho mao ang pangitaon ang mga pulong nga Ingles "
            "ug ilisan kini sa husto nga Cebuano o phonetically spelled nga porma.\n\n"
            "MGA LAGDA:\n"
            "- Pangitaa ang TANAN nga pulong nga Ingles sa text\n"
            "- Ilisan sa Cebuano nga katumbas o phonetically spelled nga porma (gamit ang mga gitling)\n"
            "- Ang mga pangalan sa tawo ug lugar DILI isulat pag-usab (hal. Pepito, Catanduanes, Luzon)\n"
            "- Ayaw usba ang bisan unsang butang nga dili Ingles\n"
            "- Ibalik ang TIBUOK text nga adunay mga pagbabago lamang\n"
            "- Walay markdown, walay paliwanag — plain text lamang\n\n"
            "PANANGLITAN SA PAGPULI:\n"
            "  'storm surge' → 'storm serj'\n"
            "  'landfall' → 'land-pol'\n"
            "  'coastal' → 'kos-tal'\n"
            "  'warning' → 'wor-ning'\n"
            "  'advisory' → 'ad-bay-so-ri'\n"
            "  'signal' → 'sig-nal'\n"
            "  'forecast' → 'pore-kast'\n"
            "  'emergency' → 'i-mer-chen-si'\n"
            "  'evacuation' → 'i-bak-yu-ey-syon'\n"
            "  'mo-intensify' → 'mo-kusog'\n"
        ),
        "user": (
            "Susiha kining Cebuano TTS text. Pangitaa ang tanan nga pulong nga Ingles ug ilisan sa "
            "Cebuano o phonetically spelled nga porma. Ibalik ang tibuok text nga adunay mga pagbabago.\n\n"
            "{text}"
        ),
    },
}

_NUMBER_CLEANUP_PROMPTS = {
    "tl": {
        "system": (
            "Ikaw ay isang editor ng Tagalog TTS text. Ang iyong trabaho ay hanapin ang LAHAT ng numerong nakasulat "
            "bilang mga digit at palitan sila ng katumbas na salita sa Filipino/Spanish na sistema ng bilang.\n\n"
            "PANUNTUNAN:\n"
            "- Hanapin ang BAWAT numero na nakasulat bilang digit (0-9) sa text\n"
            "- Palitan ng spoken na anyo gamit ang Filipino/Spanish na mga salita\n"
            "- Ang mga pangalan ng tao at lugar ay HUWAG baguhin\n"
            "- Huwag baguhin ang anumang salita — digits lang ang palitan\n"
            "- Ibalik ang BUONG text na may mga pagbabago lamang\n"
            "- Walang markdown, walang paliwanag — plain text lamang\n\n"
            "MGA NUMERO AT KATUMBAS:\n"
            "  1=uno  2=dos  3=tres  4=kuwatro  5=singko\n"
            "  6=sayis  7=syete  8=otso  9=nuwebe  10=diyes\n"
            "  11=onse  12=dose  13=trese  14=katorse  15=kinse\n"
            "  16=disisayis  17=disisyete  18=diotso  19=disinuwebe\n"
            "  20=beinte  21=beinte uno  22=beinte dos  25=beinte singko\n"
            "  30=treynta  31=treynta y uno  40=kuwarenta  50=singkwenta\n"
            "  60=sisenta  70=sitenta  80=otsenta  90=nobenta\n"
            "  100=isang daan  120=isang daan beinte  130=isang daan treynta\n"
            "  150=isang daan singkwenta  200=dos siyentos\n\n"
            "HALIMBAWA:\n"
            "  'Oktubre 21' → 'Oktubre beinte uno'\n"
            "  '25 kilometro' → 'beinte singko kilometro'\n"
            "  '130 kilometro' → 'isang daan treynta kilometro'\n"
            "  'Signal 2' → 'sig-nal tu'\n"
            "  '6 ng umaga' → 'sayis ng umaga'"
        ),
        "user": (
            "Suriin ang Tagalog TTS text na ito. Palitan ang LAHAT ng digit na numero ng katumbas na salita. "
            "Ibalik ang buong text na may mga pagbabago.\n\n"
            "{text}"
        ),
    },
    "ceb": {
        "system": (
            "Ikaw usa ka editor sa Cebuano TTS text. Ang imong trabaho mao ang pangitaon ang TANAN nga numero nga "
            "gisulat isip mga digit ug ilisan kini sa katumbas nga pulong sa Cebuano/Spanish nga sistema sa ihap.\n\n"
            "MGA LAGDA:\n"
            "- Pangitaa ang MATAG numero nga gisulat isip digit (0-9) sa text\n"
            "- Ilisan sa spoken nga porma gamit ang Cebuano/Spanish nga mga pulong\n"
            "- Ang mga pangalan sa tawo ug lugar DILI usbon\n"
            "- Ayaw usba ang bisan unsang pulong — ang mga digit lang ang ilisan\n"
            "- Ibalik ang TIBUOK text nga adunay mga pagbabago lamang\n"
            "- Walay markdown, walay paliwanag — plain text lamang\n\n"
            "MGA NUMERO UG PASABOT:\n"
            "  1=uno  2=dos  3=tres  4=kuwatro  5=singko\n"
            "  6=sayis  7=syete  8=otso  9=nuwebe  10=diyes\n"
            "  11=onse  12=dose  13=trese  14=katorse  15=kinse\n"
            "  16=disisayis  17=disisyete  18=diotso  19=disinuwebe\n"
            "  20=baynte  21=baynte uno  22=baynte dos  25=baynte singko\n"
            "  30=treynta  31=treynta y uno  40=kuwarenta  50=singkwenta\n"
            "  60=sisenta  70=sitenta  80=otsenta  90=nobenta\n"
            "  100=isyento  120=isyento baynte  130=isyento treynta\n"
            "  150=isyento singkwenta  200=dos siyentos\n\n"
            "PANANGLITAN:\n"
            "  'Oktubre 21' → 'Oktubre baynte uno'\n"
            "  '25 kilometros' → 'baynte singko kilometros'\n"
            "  '130 kilometros' → 'isyento treynta kilometros'\n"
            "  'Signal 2' → 'sig-nal tu'\n"
            "  '6 sa buntag' → 'sayis sa buntag'"
        ),
        "user": (
            "Susiha kining Cebuano TTS text. Ilisan ang TANAN nga digit nga numero sa katumbas nga pulong. "
            "Ibalik ang tibuok text nga adunay mga pagbabago.\n\n"
            "{text}"
        ),
    },
}


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _format_metadata_for_prompt(metadata: dict) -> str:
    """Convert a parsed metadata.json dict into a labelled text block for LLM prompts."""
    s = metadata.get("storm", {})
    storm_name = s.get("name", "Unknown")
    category = s.get("category", "Unknown")
    intl = s.get("international_name")
    intl_str = f" (international name: {intl})" if intl else ""

    b_type = metadata.get("bulletin_type", "")
    b_num = metadata.get("bulletin_number")
    b_num_str = f" #{b_num}" if b_num else ""
    bulletin_label = f"{b_type}{b_num_str}" if b_type else "Bulletin"

    iss = metadata.get("issuance", {})
    issued = iss.get("datetime") or "not specified"
    valid_until = iss.get("valid_until") or "not specified"

    pos = metadata.get("current_position", {})
    position_ref = pos.get("reference") or "not specified"
    position_as_of = pos.get("as_of") or ""
    position_str = position_ref
    if position_as_of:
        position_str += f" (as of {position_as_of})"

    inten = metadata.get("intensity", {})
    winds = inten.get("max_sustained_winds_kph")
    gusts = inten.get("gusts_kph")
    winds_str = f"{winds} km/h" if winds else "not specified"
    gusts_str = f"up to {gusts} km/h" if gusts else "not specified"

    mov = metadata.get("movement", {})
    direction = mov.get("direction") or "not specified"
    speed = mov.get("speed_kph")
    speed_str = f"{speed} km/h" if speed else "not specified"

    areas = metadata.get("affected_areas", {})
    signal_sections = []
    for level in range(1, 6):
        places = areas.get(f"signal_{level}", [])
        if places:
            signal_sections.append(f"  Signal {level}: {', '.join(places)}")
    rainfall = areas.get("rainfall_warning", [])
    if rainfall:
        signal_sections.append(f"  Rainfall warning: {', '.join(rainfall)}")
    coastal = areas.get("coastal_waters")
    if coastal:
        signal_sections.append(f"  Coastal waters: {coastal}")
    signals_str = (
        "\n".join(signal_sections)
        if signal_sections
        else "  No wind signals in effect — no areas of the Philippines are under any wind signal."
    )

    forecasts = metadata.get("forecast_positions", [])
    forecast_lines = [
        f"  {fp.get('hour', '?')}-hour: {fp.get('reference') or 'location not specified'}"
        for fp in forecasts
    ]
    forecasts_str = "\n".join(forecast_lines) if forecast_lines else "  Not available"

    return (
        f"=== PAGASA TYPHOON BULLETIN ===\n"
        f"Storm: {category} {storm_name}{intl_str}\n"
        f"Bulletin: {bulletin_label}\n"
        f"Issued: {issued}\n"
        f"Valid until / Next bulletin: {valid_until}\n"
        f"\n"
        f"CURRENT POSITION:\n"
        f"  {position_str}\n"
        f"\n"
        f"INTENSITY:\n"
        f"  Maximum sustained winds: {winds_str} near the center\n"
        f"  Gusts: {gusts_str}\n"
        f"\n"
        f"MOVEMENT:\n"
        f"  Direction: {direction}\n"
        f"  Speed: {speed_str}\n"
        f"\n"
        f"WIND SIGNALS IN EFFECT:\n"
        f"{signals_str}\n"
        f"\n"
        f"FORECAST TRACK:\n"
        f"{forecasts_str}\n"
    )


def _clean_ocr(text: str) -> str:
    """Remove OCR artefacts: lines that are entirely a [BRACKET LABEL]."""
    text = re.sub(r"^\s*\[[^\]\n]+\]\s*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _generate_radio_script(
    ocr_md: str, language: str, ollama_url: str, model: str, metadata: dict | None = None
) -> str:
    if metadata is not None:
        bulletin_data = (
            "=== KEY FACTS (use these for accuracy — do not confuse fields) ===\n"
            f"{_format_metadata_for_prompt(metadata)}\n"
            "=== FULL BULLETIN TEXT (use for completeness) ===\n"
            f"{ocr_md}"
        )
    else:
        bulletin_data = ocr_md
    p = _RADIO_PROMPTS[language]
    return call_ollama_chat(
        url=ollama_url,
        model=model,
        system=p["system"],
        user=p["user"].format(bulletin_data=bulletin_data),
    )


def _generate_tts_text(radio_md: str, language: str, ollama_url: str, model: str) -> str:
    p = _TTS_PROMPTS[language]
    text = call_ollama_chat(
        url=ollama_url,
        model=model,
        system=p["system"],
        user=p["user"].format(markdown=radio_md),
    )
    return apply_phonetics(text, language)


def _cleanup_english_words(text: str, language: str, ollama_url: str, model: str) -> str:
    if language not in _CLEANUP_PROMPTS:
        return text
    p = _CLEANUP_PROMPTS[language]
    return call_ollama_chat(
        url=ollama_url,
        model=model,
        system=p["system"],
        user=p["user"].format(text=text),
    )


def _cleanup_numbers(text: str, language: str, ollama_url: str, model: str) -> str:
    if language not in _NUMBER_CLEANUP_PROMPTS:
        return text
    p = _NUMBER_CLEANUP_PROMPTS[language]
    return call_ollama_chat(
        url=ollama_url,
        model=model,
        system=p["system"],
        user=p["user"].format(text=text),
    )


# ---------------------------------------------------------------------------
# Public runner
# ---------------------------------------------------------------------------

def run_step2(
    stem: str,
    language: str,
    output_dir: Path,
    ollama_url: str = "http://localhost:11434",
    model: str = "gemma4:e4b",
    force: bool = False,
) -> Path:
    """Generate radio script and TTS plain text for one bulletin + language.

    Reads:  output_dir/{stem}/ocr.md  (required)
            output_dir/{stem}/metadata.json  (optional — falls back to OCR-only)
    Writes: output_dir/{stem}/radio_{language}.md
            output_dir/{stem}/tts_{language}.txt

    Returns:
        Path to radio_{language}.md on success.
    """
    out_dir = output_dir / stem
    radio_path = out_dir / f"radio_{language}.md"
    tts_path = out_dir / f"tts_{language}.txt"

    if radio_path.exists() and tts_path.exists() and not force:
        print(f"[run_step2] {stem}/{language}: already exists, skipping")
        return radio_path

    ocr_file = out_dir / "ocr.md"
    if not ocr_file.exists():
        raise FileNotFoundError(f"[run_step2] ocr.md not found at {ocr_file}. Run step 1 first.")

    ocr_md = _clean_ocr(ocr_file.read_text(encoding="utf-8"))

    metadata_path = out_dir / "metadata.json"
    if metadata_path.exists():
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        print(f"[run_step2] {stem}/{language}: using hybrid input (metadata + OCR)")
    else:
        metadata = None
        print(f"[run_step2] {stem}/{language}: metadata.json absent, using OCR only")

    radio_md = _generate_radio_script(ocr_md, language, ollama_url, model, metadata=metadata)
    radio_path.write_text(radio_md, encoding="utf-8")

    tts_text = _generate_tts_text(radio_md, language, ollama_url, model)
    tts_text = _cleanup_english_words(tts_text, language, ollama_url, model)
    tts_text = _cleanup_numbers(tts_text, language, ollama_url, model)
    tts_path.write_text(tts_text, encoding="utf-8")

    print(f"[run_step2] {stem}/{language}: wrote radio + tts files")
    return radio_path
```

- [ ] **Step 3.5: Run tests to verify they pass**

```bash
uv run pytest tests/test_step2_format_metadata.py tests/test_core_scripts.py -v
```
Expected: all tests PASS.

- [ ] **Step 3.6: Replace `step2_scripts.py` with a thin Modal wrapper**

Completely replace `modal_etl/step2_scripts.py` with:

```python
import os
import subprocess

from modal_etl.app import app, ollama_image, OLLAMA_MOUNTS, output_volume
from modal_etl.config import OLLAMA_MODELS_PATH, OUTPUT_PATH, GEMMA_MODEL
from modal_etl.core.ollama import wait_for_ollama
from modal_etl.core.scripts import run_step2

OLLAMA_URL = "http://localhost:11434"


@app.function(
    image=ollama_image,
    gpu="A10G",
    volumes=OLLAMA_MOUNTS,
    timeout=600,
)
def step2_scripts(stem: str, language: str, force: bool = False) -> str:
    """Generate radio script and TTS plain text for one bulletin + language.

    Runs one language per container so all three languages execute in parallel
    via starmap (same pattern as step3_tts).

    Reads:   /output/{stem}/ocr.md
    Writes:  /output/{stem}/radio_{language}.md
             /output/{stem}/tts_{language}.txt

    Returns:
        stem string.
    """
    os.environ["OLLAMA_MODELS"] = str(OLLAMA_MODELS_PATH)
    subprocess.Popen(["ollama", "serve"])
    wait_for_ollama(OLLAMA_URL)
    print(f"[Step2Scripts] Ollama ready ({language})")
    run_step2(stem, language, OUTPUT_PATH, OLLAMA_URL, GEMMA_MODEL, force)
    output_volume.commit()
    return stem
```

- [ ] **Step 3.7: Run all tests to verify no regressions**

```bash
uv run pytest tests/ -v
```
Expected: all tests PASS.

- [ ] **Step 3.8: Commit**

```bash
git add modal_etl/core/scripts.py tests/test_core_scripts.py modal_etl/step2_scripts.py tests/test_step2_format_metadata.py
git commit -m "feat: extract script generation logic into modal_etl/core/scripts.py, step2_scripts becomes thin wrapper"
```

---

## Task 4: Create `modal_etl/core/tts.py` and refactor `step3_tts.py`

**Files:**
- Create: `modal_etl/core/tts.py`
- Create: `tests/test_core_tts.py`
- Modify: `modal_etl/step3_tts.py` (full replacement with thin wrapper)
- Modify: `tests/test_step3_sentences.py` (update import)

- [ ] **Step 4.1: Update import in `tests/test_step3_sentences.py`**

Change lines:
```python
from modal_etl.step3_tts import prepare_mms_sentences, prepare_english_sentences
```
to:
```python
from modal_etl.core.tts import prepare_mms_sentences, prepare_english_sentences
```

- [ ] **Step 4.2: Write additional failing tests**

Create `tests/test_core_tts.py`:

```python
"""Tests for modal_etl/core/tts.py — skip logic and error handling for run_step3."""
import pytest
from pathlib import Path
from modal_etl.core.tts import run_step3


def test_run_step3_skips_when_mp3_exists(tmp_path):
    """run_step3 returns mp3_path immediately when audio file exists and force=False."""
    stem = "PAGASA_TEST"
    stem_dir = tmp_path / stem
    stem_dir.mkdir()
    (stem_dir / "tts_en.txt").write_text("Hello world.", encoding="utf-8")
    mp3_path = stem_dir / "audio_en.mp3"
    mp3_path.write_bytes(b"fake mp3")

    result = run_step3(stem, "en", tmp_path, tmp_path / "models", force=False)

    assert result == mp3_path


def test_run_step3_raises_for_unknown_language(tmp_path):
    """run_step3 raises ValueError for an unrecognised language code."""
    stem = "PAGASA_TEST"
    stem_dir = tmp_path / stem
    stem_dir.mkdir()
    (stem_dir / "tts_xx.txt").write_text("text", encoding="utf-8")

    with pytest.raises(ValueError, match="Unknown language"):
        run_step3(stem, "xx", tmp_path, tmp_path / "models", force=True)


def test_run_step3_raises_when_tts_text_missing(tmp_path):
    """run_step3 raises FileNotFoundError when tts_{lang}.txt does not exist."""
    stem = "PAGASA_TEST"
    stem_dir = tmp_path / stem
    stem_dir.mkdir()

    with pytest.raises(FileNotFoundError, match="tts_en.txt"):
        run_step3(stem, "en", tmp_path, tmp_path / "models", force=True)
```

- [ ] **Step 4.3: Run tests to verify they fail**

```bash
uv run pytest tests/test_step3_sentences.py tests/test_core_tts.py -v
```
Expected: `ImportError` for `test_step3_sentences.py`, `ImportError` for `test_core_tts.py`.

- [ ] **Step 4.4: Create `modal_etl/core/tts.py`**

```python
import re
from pathlib import Path

from modal_etl.synthesizers.mms import MMSSynthesizer
from modal_etl.synthesizers.xtts import CoquiXTTSSynthesizer


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
            cleaned = sentence.lower()
            cleaned = re.sub(r"[^\w\s'\-]", " ", cleaned)
            cleaned = re.sub(r"(?<!\w)['\-]|['\-](?!\w)", " ", cleaned)
            cleaned = re.sub(r"\s+", " ", cleaned).strip()
            if cleaned:
                result.append((cleaned, is_last))
    return result


def prepare_english_sentences(text: str) -> list[tuple[str, bool]]:
    """Split plain text into XTTS-ready sentences.

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


_SYNTHESIZER_FACTORIES = {
    "ceb": lambda cache_dir: MMSSynthesizer("facebook/mms-tts-ceb", cache_dir=cache_dir),
    "tl": lambda cache_dir: MMSSynthesizer("facebook/mms-tts-tgl", cache_dir=cache_dir),
    "en": lambda cache_dir: CoquiXTTSSynthesizer(cache_dir=cache_dir),
}


def run_step3(
    stem: str,
    language: str,
    output_dir: Path,
    tts_models_dir: Path,
    force: bool = False,
) -> Path:
    """Synthesize TTS plain text to MP3 for one bulletin + language.

    Reads:  output_dir/{stem}/tts_{language}.txt
    Writes: output_dir/{stem}/audio_{language}.mp3

    Returns:
        Path to audio_{language}.mp3 on success.
    """
    out_dir = output_dir / stem
    tts_txt_path = out_dir / f"tts_{language}.txt"
    mp3_path = out_dir / f"audio_{language}.mp3"

    if mp3_path.exists() and not force:
        print(f"[run_step3] {stem}/{language}: already exists, skipping")
        return mp3_path

    if language not in _SYNTHESIZER_FACTORIES:
        raise ValueError(
            f"[run_step3] Unknown language '{language}'. Expected one of: {list(_SYNTHESIZER_FACTORIES)}"
        )

    if not tts_txt_path.exists():
        raise FileNotFoundError(
            f"[run_step3] Input not found: {tts_txt_path}. Run step 2 first."
        )

    text = tts_txt_path.read_text(encoding="utf-8")
    synthesizer = _SYNTHESIZER_FACTORIES[language](tts_models_dir)
    synthesizer.load()

    if language == "en":
        sentences = prepare_english_sentences(text)
    else:
        sentences = prepare_mms_sentences(text)

    synthesizer.synthesize(sentences, mp3_path)
    print(f"[run_step3] {stem}/{language}: wrote {mp3_path}")
    return mp3_path
```

- [ ] **Step 4.5: Run tests to verify they pass**

```bash
uv run pytest tests/test_step3_sentences.py tests/test_core_tts.py -v
```
Expected: all tests PASS.

- [ ] **Step 4.6: Replace `step3_tts.py` with a thin Modal wrapper**

Completely replace `modal_etl/step3_tts.py` with:

```python
from modal_etl.app import app, tts_image, TTS_MOUNTS, output_volume
from modal_etl.config import TTS_MODELS_PATH, OUTPUT_PATH
from modal_etl.core.tts import run_step3


@app.function(
    image=tts_image,
    gpu="A10G",
    volumes=TTS_MOUNTS,
    timeout=600,
)
def step3_tts(stem: str, language: str, force: bool = False) -> str:
    """Synthesize TTS plain text for one bulletin + language to MP3.

    Reads:  /output/{stem}/tts_{language}.txt
    Writes: /output/{stem}/audio_{language}.mp3

    Returns:
        stem on success.
    """
    run_step3(stem, language, OUTPUT_PATH, TTS_MODELS_PATH, force)
    output_volume.commit()
    print(f"[Step3TTS] {stem}/{language}: done")
    return stem
```

- [ ] **Step 4.7: Run all tests to verify no regressions**

```bash
uv run pytest tests/ -v
```
Expected: all tests PASS.

- [ ] **Step 4.8: Commit**

```bash
git add modal_etl/core/tts.py tests/test_core_tts.py modal_etl/step3_tts.py tests/test_step3_sentences.py
git commit -m "feat: extract TTS logic into modal_etl/core/tts.py, step3_tts becomes thin wrapper"
```

---

## Task 5: Create notebook 10 — end-to-end local pipeline

**Files:**
- Create: `notebooks/10-etl-e2e.ipynb`

- [ ] **Step 5.1: Verify imports work from notebook context**

```bash
cd notebooks && uv run python -c "
import sys
sys.path.insert(0, '..')
from modal_etl.core.ocr import run_step1
from modal_etl.core.scripts import run_step2
from modal_etl.core.tts import run_step3
print('All core imports OK')
"
```
Expected output: `All core imports OK`

- [ ] **Step 5.2: Create `notebooks/10-etl-e2e.ipynb`**

Create the file using Python to generate valid notebook JSON:

```bash
uv run python - << 'PYEOF'
import json
from pathlib import Path

cells = [
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "# End-to-End ETL Pipeline (Local)\n",
            "\n",
            "Runs the full WeatherSpeak PH pipeline locally using `modal_etl/core/` modules.\n",
            "\n",
            "**Pipeline:** PDF → OCR markdown + metadata → radio scripts + TTS text → MP3\n",
            "\n",
            "The same `run_step1 / run_step2 / run_step3` functions are used by the Modal ETL in production.\n",
            "Output mirrors the Modal Volume layout: `output/{stem}/ocr.md`, `radio_{lang}.md`, etc.\n",
            "\n",
            "Set `force=True` in any step cell to re-run that step even if outputs already exist."
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "import sys\n",
            "from pathlib import Path\n",
            "\n",
            "# Make modal_etl importable from notebook directory\n",
            "sys.path.insert(0, str(Path.cwd().parent))\n",
            "\n",
            "from modal_etl.core.ocr import run_step1\n",
            "from modal_etl.core.scripts import run_step2\n",
            "from modal_etl.core.tts import run_step3"
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# ── Configuration ────────────────────────────────────────────────────────\n",
            "STEM          = \"PAGASA_22-TC02_Basyang_TCA#01\"\n",
            "PDF_PATH      = Path(\"../data/bulletin-archive/archive/pagasa-22-TC02\") / f\"{STEM}.pdf\"\n",
            "OUTPUT_DIR    = Path(\"10-etl-e2e/output\")\n",
            "OLLAMA_URL    = \"http://localhost:11434\"\n",
            "LANGUAGES     = [\"en\", \"tl\", \"ceb\"]\n",
            "TTS_MODELS_DIR = Path.home() / \".cache\" / \"huggingface\" / \"hub\"\n",
            "\n",
            "OUTPUT_DIR.mkdir(parents=True, exist_ok=True)\n",
            "print(f\"PDF:        {PDF_PATH}  (exists={PDF_PATH.exists()})\")\n",
            "print(f\"Output dir: {OUTPUT_DIR.resolve()}\")\n",
            "print(f\"Ollama URL: {OLLAMA_URL}\")"
        ]
    },
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": ["## Step 1: OCR — PDF → Markdown + Metadata\n",
                   "\n",
                   "Sends each PDF page to Gemma 4 E4B via Ollama vision API.\n",
                   "Writes `ocr.md`, `chart.png`, and `metadata.json` to `output/{stem}/`."]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "stem_dir = run_step1(PDF_PATH, OUTPUT_DIR, ollama_url=OLLAMA_URL, force=False)\n",
            "print(f\"\\nStep 1 complete → {stem_dir}\")\n",
            "\n",
            "# Preview OCR markdown\n",
            "ocr_md = (stem_dir / \"ocr.md\").read_text(encoding=\"utf-8\")\n",
            "print(f\"\\n--- ocr.md preview (first 500 chars) ---\")\n",
            "print(ocr_md[:500])\n",
            "\n",
            "# Pretty-print metadata\n",
            "import json\n",
            "metadata = json.loads((stem_dir / \"metadata.json\").read_text(encoding=\"utf-8\"))\n",
            "print(f\"\\n--- metadata.json ---\")\n",
            "print(json.dumps(metadata, indent=2, ensure_ascii=False)[:1000])"
        ]
    },
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": ["## Step 2: Radio Scripts + TTS Text\n",
                   "\n",
                   "Generates a spoken weather announcement and TTS-optimised plain text for each language.\n",
                   "Writes `radio_{lang}.md` and `tts_{lang}.txt` to `output/{stem}/`."]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "for lang in LANGUAGES:\n",
            "    radio_path = run_step2(STEM, lang, OUTPUT_DIR, ollama_url=OLLAMA_URL, force=False)\n",
            "    print(f\"\\n{'='*60}\")\n",
            "    print(f\"[{lang.upper()}] {radio_path.name}\")\n",
            "    print('='*60)\n",
            "    print(radio_path.read_text(encoding=\"utf-8\")[:400])\n",
            "print(\"\\nStep 2 complete.\")"
        ]
    },
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": ["## Step 3: TTS Synthesis → MP3\n",
                   "\n",
                   "Synthesizes MP3 audio for each language using:\n",
                   "- English: Coqui XTTS v2 (speaker: Damien Black)\n",
                   "- Tagalog / Cebuano: Facebook MMS VITS\n",
                   "\n",
                   "Writes `audio_{lang}.mp3` to `output/{stem}/`."]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "for lang in LANGUAGES:\n",
            "    mp3_path = run_step3(STEM, lang, OUTPUT_DIR, TTS_MODELS_DIR, force=False)\n",
            "    size_kb = mp3_path.stat().st_size // 1024\n",
            "    print(f\"[{lang.upper()}] {mp3_path.name}  ({size_kb} KB)\")\n",
            "print(\"\\nStep 3 complete.\")"
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "from IPython.display import Audio, display, Markdown\n",
            "\n",
            "for lang in LANGUAGES:\n",
            "    mp3_path = OUTPUT_DIR / STEM / f\"audio_{lang}.mp3\"\n",
            "    if mp3_path.exists():\n",
            "        display(Markdown(f\"**{lang.upper()}**\"))\n",
            "        display(Audio(str(mp3_path)))"
        ]
    },
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": ["## Output Summary"]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "stem_dir = OUTPUT_DIR / STEM\n",
            "print(f\"Artefacts in {stem_dir.resolve()}:\\n\")\n",
            "for f in sorted(stem_dir.iterdir()):\n",
            "    size = f.stat().st_size\n",
            "    unit = 'KB' if size >= 1024 else 'B'\n",
            "    val = size // 1024 if size >= 1024 else size\n",
            "    print(f\"  {f.name:<35}  {val:>6} {unit}\")"
        ]
    }
]

nb = {
    "nbformat": 4,
    "nbformat_minor": 5,
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.12.0"}
    },
    "cells": cells
}

out = Path("notebooks/10-etl-e2e.ipynb")
out.write_text(json.dumps(nb, indent=1, ensure_ascii=False))
print(f"Created {out}  ({out.stat().st_size} bytes, {len(cells)} cells)")
PYEOF
```

- [ ] **Step 5.3: Verify the notebook is valid JSON with correct cell count**

```bash
uv run python -c "
import json
from pathlib import Path
nb = json.loads(Path('notebooks/10-etl-e2e.ipynb').read_text())
print('Valid JSON ✓')
print(f'Cells: {len(nb[\"cells\"])}')
for i, c in enumerate(nb['cells']):
    ct = c['cell_type']
    src = ''.join(c['source'])[:60].replace(chr(10), ' ')
    print(f'  [{i}] {ct}: {src}')
"
```
Expected: 11 cells, types alternating markdown/code as designed.

- [ ] **Step 5.4: Commit**

```bash
git add notebooks/10-etl-e2e.ipynb
git commit -m "feat: add notebook 10 end-to-end local ETL pipeline using modal_etl/core"
```

---

## Self-Review Checklist

**Spec coverage:**
- ✅ `modal_etl/core/__init__.py` — Task 1
- ✅ `modal_etl/core/ollama.py` with `wait_for_ollama`, `call_ollama_generate`, `call_ollama_chat` — Task 1
- ✅ `modal_etl/core/ocr.py` with `run_step1` + `PAGASA_JSON_SCHEMA` — Task 2
- ✅ `modal_etl/core/scripts.py` with `run_step2` — Task 3
- ✅ `modal_etl/core/tts.py` with `run_step3` + sentence prep — Task 4
- ✅ Step files refactored to thin wrappers — Tasks 2, 3, 4
- ✅ Public signatures of step functions unchanged — Tasks 2, 3, 4
- ✅ `force=False` skip logic in all three `run_step*` functions — Tasks 2, 3, 4
- ✅ Notebook 10 with 11 cells matching spec layout — Task 5
- ✅ PDF path uses `data/bulletin-archive/archive/pagasa-22-TC02/` (actual location) — Task 5
- ✅ Output dir `10-etl-e2e/output/{stem}/` mirrors Modal Volume — Task 5
- ✅ `_format_metadata_for_prompt` and sentence prep tests updated to new import paths — Tasks 3, 4
- ✅ `PAGASA_JSON_SCHEMA` import in `test_schema_validation.py` updated — Task 2
- ✅ `_wait_for_ollama` deduplication — Task 1

**Type consistency:** All calls to `run_step1(pdf_path, output_dir, ...)`, `run_step2(stem, language, output_dir, ...)`, `run_step3(stem, language, output_dir, tts_models_dir, ...)` match their definitions across all tasks and notebook cells.
