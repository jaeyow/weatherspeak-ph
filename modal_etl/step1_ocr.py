import subprocess
import tempfile
from pathlib import Path
from urllib.parse import unquote

import modal
import requests

from modal_etl.app import app, ollama_image, marker_image, OLLAMA_MOUNTS, output_volume
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
    def run(self, pdf_url: str, force: bool = False, backend: str = "marker") -> str:
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
        run_step1(pdf_path, OUTPUT_PATH, OLLAMA_URL, GEMMA_MODEL, force, stem=stem, backend=backend)
        output_volume.commit()
        return stem


@app.cls(
    image=marker_image,
    gpu="A10G",
    volumes=OLLAMA_MOUNTS,
    timeout=3600,
)
class Step1OCRMarker:
    @modal.enter()
    def start_ollama(self) -> None:
        """Start Ollama server (needed for chart description pass)."""
        import os
        os.environ["OLLAMA_MODELS"] = str(OLLAMA_MODELS_PATH)
        subprocess.Popen(["ollama", "serve"])
        wait_for_ollama(OLLAMA_URL)
        print("[Step1OCRMarker] Ollama ready")

    @modal.method()
    def run(self, pdf_url: str, force: bool = False) -> str:
        """Download PDF and run Marker OCR pipeline.

        Returns:
            stem string (filename without .pdf extension).
        """
        stem = unquote(pdf_url.split("/")[-1].replace(".pdf", ""))
        resp = requests.get(pdf_url, timeout=60)
        resp.raise_for_status()
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(resp.content)
            pdf_path = Path(f.name)
        run_step1(pdf_path, OUTPUT_PATH, OLLAMA_URL, GEMMA_MODEL, force, stem=stem, backend="marker")
        output_volume.commit()
        return stem
