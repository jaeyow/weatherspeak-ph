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
