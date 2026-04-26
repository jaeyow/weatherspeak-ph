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
