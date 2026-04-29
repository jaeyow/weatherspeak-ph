import modal
from modal_etl.config import (
    OLLAMA_VOLUME_NAME,
    TTS_VOLUME_NAME,
    OUTPUT_VOLUME_NAME,
    OLLAMA_MODELS_PATH,
    TTS_MODELS_PATH,
    OUTPUT_PATH,
)

SUPABASE_SECRET = modal.Secret.from_name("weatherspeak-supabase")

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

# Shared base for Ollama-based images — add_local_python_source must come last
# in each final image so Modal doesn't try to run pip_install after a local mount.
_ollama_base = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("curl", "poppler-utils", "ffmpeg", "zstd")
    .run_commands("curl -fsSL https://ollama.ai/install.sh | sh")
    .pip_install(
        "requests>=2.32.0",
        "Pillow>=10.0.0",
        "pdf2image>=1.17.0",
    )
)

# Container image for steps 1 & 2 (Ollama + Gemma 4)
ollama_image = _ollama_base.add_local_python_source("modal_etl")

# Container image for Step 1 in Marker mode.
# Install CUDA torch before marker-pdf so surya-ocr uses the GPU.
# No <1.7.0 upper bound here — marker_image has no coqui-tts so it is free
# to use marker 1.7+ (surya-ocr>=0.17, transformers>=4.56). The <1.7.0 pin
# in pyproject.toml only exists to protect the local venv where coqui-tts
# forces transformers<=4.46.2.
# add_local_python_source must be last — no build steps after a local mount.
marker_image = (
    _ollama_base
    .pip_install("torch>=2.2.0", extra_index_url="https://download.pytorch.org/whl/cu121")
    .pip_install("marker-pdf>=1.7.0,<1.8.0")
    .add_local_python_source("modal_etl")
)

# Container image for step 4 (Supabase upload) — lightweight, no ML deps
upload_image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install(
        "supabase>=2.0.0",
        "python-dateutil>=2.9.0",
        "mutagen>=1.47.0",
    )
    .add_local_python_source("modal_etl")
)

# Container image for step 3 (MMS + Coqui XTTS v2) — GPU for fast XTTS v2 synthesis
# torch must be installed with CUDA support — default PyPI torch is CPU-only
tts_image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("ffmpeg")
    .pip_install(
        "torch>=2.2.0",
        extra_index_url="https://download.pytorch.org/whl/cu121",
    )
    .pip_install(
        "transformers>=4.43.0,<=4.46.2",
        "pydub>=0.25.1",
        "numpy>=1.26.0",
        "coqui-tts>=0.25.0",
    )
    .add_local_python_source("modal_etl")
)
