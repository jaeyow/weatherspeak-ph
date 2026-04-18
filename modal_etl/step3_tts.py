import re

from modal_etl.app import app, tts_image, TTS_MOUNTS, output_volume
from modal_etl.config import TTS_MODELS_PATH, OUTPUT_PATH
from modal_etl.synthesizers.mms import MMSSynthesizer
from modal_etl.synthesizers.xtts import CoquiXTTSSynthesizer

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
    "en": CoquiXTTSSynthesizer(
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
            cleaned = sentence.lower()
            cleaned = re.sub(r"[^\w\s'\-]", " ", cleaned)
            cleaned = re.sub(r"(?<!\w)['\-]|['\-](?!\w)", " ", cleaned)
            cleaned = re.sub(r"\s+", " ", cleaned).strip()
            if cleaned:
                result.append((cleaned, is_last))
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
    gpu="A10G",
    volumes=TTS_MOUNTS,
    timeout=600,  # cold start + XTTS v2 model load ~120s, synthesis ~60s on GPU
)
def step3_tts(stem: str, language: str, force: bool = False) -> str:
    """Synthesize TTS plain text for one bulletin + language to MP3.

    Reads:  /output/{stem}/tts_{language}.txt
    Writes: /output/{stem}/audio_{language}.mp3

    Skips synthesis if audio_{language}.mp3 already exists, unless force=True.

    Returns:
        stem on success.
    """
    out_dir = OUTPUT_PATH / stem
    tts_txt_path = out_dir / f"tts_{language}.txt"
    mp3_path = out_dir / f"audio_{language}.mp3"

    if mp3_path.exists() and not force:
        print(f"[Step3TTS] {stem}/{language}: already exists, skipping")
        return stem

    if language not in SYNTHESIZER_MAP:
        raise ValueError(
            f"[Step3TTS] Unknown language '{language}'. Expected one of: {list(SYNTHESIZER_MAP)}"
        )

    if not tts_txt_path.exists():
        raise FileNotFoundError(
            f"[Step3TTS] Input not found: {tts_txt_path}. Run step2 first."
        )

    text = tts_txt_path.read_text(encoding="utf-8")

    synthesizer = SYNTHESIZER_MAP[language]
    synthesizer.load()

    if language == "en":
        sentences = prepare_english_sentences(text)
    else:
        sentences = prepare_mms_sentences(text)

    synthesizer.synthesize(sentences, mp3_path)
    output_volume.commit()

    print(f"[Step3TTS] {stem}/{language}: wrote {mp3_path}")
    return stem
