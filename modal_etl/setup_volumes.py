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
            requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
            return
        except (requests.exceptions.ConnectionError, requests.exceptions.ReadTimeout):
            time.sleep(delay)
    raise RuntimeError("Ollama server did not start")


@app.function(
    image=ollama_image,
    gpu="A10G",
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
    print(f"Done — {GEMMA_MODEL} is in weatherspeak-ollama volume")


@app.function(
    image=tts_image,
    volumes={str(TTS_MODELS_PATH): tts_volume},
    timeout=3600,
)
def setup_tts_volume() -> None:
    """Download MMS (CEB/TL) and Coqui XTTS v2 (EN) weights into the weatherspeak-tts-models Volume.

    Run once: uv run modal run modal_etl/setup_volumes.py::setup_tts_volume
    """
    import os
    from transformers import VitsModel, AutoTokenizer

    print("Downloading facebook/mms-tts-ceb...")
    AutoTokenizer.from_pretrained("facebook/mms-tts-ceb", cache_dir=TTS_MODELS_PATH)
    VitsModel.from_pretrained("facebook/mms-tts-ceb", cache_dir=TTS_MODELS_PATH)

    print("Downloading facebook/mms-tts-tgl...")
    AutoTokenizer.from_pretrained("facebook/mms-tts-tgl", cache_dir=TTS_MODELS_PATH)
    VitsModel.from_pretrained("facebook/mms-tts-tgl", cache_dir=TTS_MODELS_PATH)

    print("Downloading Coqui XTTS v2 (English)...")
    os.environ["COQUI_TOS_AGREED"] = "1"
    os.environ["TTS_HOME"] = str(TTS_MODELS_PATH)
    from TTS.api import TTS
    TTS("tts_models/multilingual/multi-dataset/xtts_v2")

    tts_volume.commit()
    print("Done — all TTS models are in weatherspeak-tts-models volume")
