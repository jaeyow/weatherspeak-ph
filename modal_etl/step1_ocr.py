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
OLLAMA_TIMEOUT = 600  # seconds per page — vision inference on A10G can take 2-5 min

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


def _wait_for_ollama(retries: int = 60, delay: float = 2.0) -> None:
    """Block until Ollama server responds or raise RuntimeError."""
    for _ in range(retries):
        try:
            requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
            return
        except (requests.exceptions.ConnectionError, requests.exceptions.ReadTimeout):
            time.sleep(delay)
    raise RuntimeError("Ollama server did not start within timeout")


def _call_ollama(
    prompt: str,
    system: str | None = None,
    images_b64: list[str] | None = None,
    fmt: dict | None = None,
) -> str:
    """Send a generate request to Ollama. Returns the response text."""
    payload: dict = {"model": GEMMA_MODEL, "prompt": prompt, "stream": False}
    if system:
        payload["system"] = system
    if images_b64:
        payload["images"] = images_b64
    if fmt:
        payload["format"] = fmt
    resp = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json=payload,
        timeout=OLLAMA_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()["response"]


def _pdf_to_pil_pages(pdf_bytes: bytes, dpi: int = 200):
    """Convert PDF bytes to a list of PIL Image objects (one per page)."""
    from pdf2image import convert_from_bytes
    return convert_from_bytes(pdf_bytes, dpi=dpi)


def _page_to_b64(pil_image) -> str:
    """Encode a PIL image as base64 PNG string."""
    buf = io.BytesIO()
    pil_image.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def _ocr_pdf(pages) -> str:
    """Run Gemma 4 E4B OCR on each page and return combined markdown."""
    pages_md = []
    for i, page in enumerate(pages):
        img_b64 = _page_to_b64(page)
        page_md = _call_ollama(
            prompt=_OCR_USER,
            system=_OCR_SYSTEM,
            images_b64=[img_b64],
        )
        pages_md.append(f"<!-- Page {i + 1} -->\n\n{page_md}")
    return "\n\n---\n\n".join(pages_md)


def _find_chart_page(pages) -> int:
    """Ask Gemma 4 which page (0-indexed) contains the storm track map.

    Falls back to the last page if the response cannot be parsed.
    """
    all_b64 = [_page_to_b64(p) for p in pages]
    prompt = (
        f"This PAGASA weather bulletin has {len(pages)} pages (0-indexed: "
        f"0 to {len(pages) - 1}). "
        "Which page contains the storm track map or weather disturbance chart? "
        "Reply with a single integer — the 0-based page index only. No explanation."
    )
    response = _call_ollama(prompt=prompt, images_b64=all_b64).strip()
    try:
        idx = int(response.split()[0])
        return max(0, min(idx, len(pages) - 1))
    except (ValueError, IndexError):
        return len(pages) - 1  # fallback: last page


def _generate_metadata(markdown: str) -> dict:
    """Extract structured bulletin data from OCR markdown using constrained decoding."""
    prompt = (
        "Here is the extracted text from a PAGASA bulletin:\n\n"
        f"{markdown}\n\n"
        "Convert this into the structured JSON schema."
    )
    raw = _call_ollama(prompt=prompt, system=_METADATA_SYSTEM, fmt=PAGASA_JSON_SCHEMA)
    return json.loads(raw)


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
        _wait_for_ollama()
        print("[Step1OCR] Ollama ready")

    @modal.method()
    def run(self, pdf_url: str, force: bool = False) -> str:
        """Download PDF and produce ocr.md, chart.png, and metadata.json.

        Skips processing if all three outputs already exist, unless force=True.

        Returns:
            stem string (filename without .pdf extension).
        """
        from urllib.parse import unquote
        stem = unquote(pdf_url.split("/")[-1].replace(".pdf", ""))
        out_dir = OUTPUT_PATH / stem
        ocr_path = out_dir / "ocr.md"
        chart_path = out_dir / "chart.png"
        metadata_path = out_dir / "metadata.json"

        if ocr_path.exists() and chart_path.exists() and metadata_path.exists() and not force:
            print(f"[Step1OCR] {stem}: all Step 1 outputs exist, skipping")
            return stem

        out_dir.mkdir(parents=True, exist_ok=True)

        resp = requests.get(pdf_url, timeout=60)
        resp.raise_for_status()
        pdf_bytes = resp.content

        pages = _pdf_to_pil_pages(pdf_bytes)

        # 1. OCR → markdown
        if not ocr_path.exists():
            markdown = _ocr_pdf(pages)
            ocr_path.write_text(markdown, encoding="utf-8")
            print(f"[Step1OCR] {stem}: wrote ocr.md ({len(markdown)} chars)")
        else:
            markdown = ocr_path.read_text(encoding="utf-8")

        # 2. Chart extraction → chart.png
        if not chart_path.exists():
            chart_idx = _find_chart_page(pages)
            pages[chart_idx].save(str(chart_path), format="PNG")
            print(f"[Step1OCR] {stem}: saved chart.png (page {chart_idx})")

        # 3. Structured metadata → metadata.json
        if not metadata_path.exists():
            metadata = _generate_metadata(markdown)
            metadata_path.write_text(
                json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            print(f"[Step1OCR] {stem}: wrote metadata.json")

        output_volume.commit()
        return stem
