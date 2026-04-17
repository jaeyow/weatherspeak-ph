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
    .apt_install("curl", "poppler-utils", "ffmpeg", "zstd")
    .run_commands("curl -fsSL https://ollama.ai/install.sh | sh")
    .pip_install(
        "requests>=2.32.0",
        "Pillow>=10.0.0",
        "pdf2image>=1.17.0",
    )
    .add_local_python_source("modal_etl")
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
        "coqui-tts>=0.25.0",
    )
    .add_local_python_source("modal_etl")
)
