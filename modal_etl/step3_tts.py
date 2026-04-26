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
