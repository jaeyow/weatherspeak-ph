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
