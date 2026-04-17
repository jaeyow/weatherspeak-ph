import numpy as np
from pathlib import Path
from pydub import AudioSegment

SAMPLE_RATE = 24_000  # XTTS v2 native sample rate


class CoquiXTTSSynthesizer:
    """TTS synthesizer backed by Coqui XTTS v2.

    Used for English — higher quality than MMS for English prose.
    Preserves capitalisation and punctuation for natural prosody.
    Do NOT pass lowercase/stripped sentences.
    """

    def __init__(
        self,
        model_name: str = "tts_models/multilingual/multi-dataset/xtts_v2",
        speaker: str = "Damien Black",
        language: str = "en",
        cache_dir: Path | None = None,
        sentence_pause_ms: int = 300,
        paragraph_pause_ms: int = 500,
    ):
        self.model_name = model_name
        self.speaker = speaker
        self.language = language
        self.cache_dir = cache_dir
        self.sentence_pause_ms = sentence_pause_ms
        self.paragraph_pause_ms = paragraph_pause_ms
        self._tts = None

    def load(self) -> None:
        """Load XTTS v2 model. Sets TTS_HOME to cache_dir if provided."""
        import os
        os.environ["COQUI_TOS_AGREED"] = "1"
        if self.cache_dir:
            os.environ["TTS_HOME"] = str(self.cache_dir)
        from TTS.api import TTS
        self._tts = TTS(self.model_name)

    def synthesize(
        self,
        sentences: list[tuple[str, bool]],
        output_path: Path,
    ) -> Path:
        """Synthesize sentences to MP3 with silence stitching.

        Args:
            sentences: list of (text, is_paragraph_end). Text should be
                       normal English — capitalisation and punctuation preserved.
            output_path: destination MP3 path.

        Returns:
            output_path on success.
        """
        if not sentences:
            raise ValueError("sentences list is empty — nothing to synthesize")

        combined = AudioSegment.empty()

        for text, is_paragraph_end in sentences:
            if not text.strip():
                continue
            wav = self._tts.tts(text=text, speaker=self.speaker, language=self.language)
            pcm = (np.array(wav) * 32_767).clip(-32_768, 32_767).astype(np.int16)
            segment = AudioSegment(
                pcm.tobytes(), frame_rate=SAMPLE_RATE, sample_width=2, channels=1
            )
            combined += segment
            pause_ms = (
                self.paragraph_pause_ms if is_paragraph_end else self.sentence_pause_ms
            )
            combined += AudioSegment.silent(duration=pause_ms, frame_rate=SAMPLE_RATE)

        combined.export(str(output_path), format="mp3", bitrate="128k")
        return output_path
