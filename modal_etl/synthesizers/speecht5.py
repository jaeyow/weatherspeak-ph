import numpy as np
import torch
from pathlib import Path
from pydub import AudioSegment

SAMPLE_RATE = 16_000  # SpeechT5 native sample rate


class SpeechT5Synthesizer:
    """TTS synthesizer backed by microsoft/speecht5_tts + speecht5_hifigan vocoder.

    Handles standard English text — preserves capitalisation and punctuation
    for natural prosody. Do NOT pass lowercase/stripped sentences.
    """

    def __init__(
        self,
        model_id: str = "microsoft/speecht5_tts",
        vocoder_id: str = "microsoft/speecht5_hifigan",
        cache_dir: Path | None = None,
        sentence_pause_ms: int = 300,
        paragraph_pause_ms: int = 500,
    ):
        self.model_id = model_id
        self.vocoder_id = vocoder_id
        self.cache_dir = cache_dir
        self.sentence_pause_ms = sentence_pause_ms
        self.paragraph_pause_ms = paragraph_pause_ms
        self._processor = None
        self._model = None
        self._vocoder = None
        self._speaker_embeddings = None

    def load(self) -> None:
        """Load SpeechT5, HiFiGAN vocoder, and initialise speaker embeddings."""
        from transformers import (
            SpeechT5Processor,
            SpeechT5ForTextToSpeech,
            SpeechT5HifiGan,
        )
        self._processor = SpeechT5Processor.from_pretrained(
            self.model_id, cache_dir=self.cache_dir
        )
        self._model = SpeechT5ForTextToSpeech.from_pretrained(
            self.model_id, cache_dir=self.cache_dir
        )
        self._vocoder = SpeechT5HifiGan.from_pretrained(
            self.vocoder_id, cache_dir=self.cache_dir
        )
        # Neutral speaker embedding — consistent across all synthesis calls
        self._speaker_embeddings = torch.zeros(1, 512)

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
            inputs = self._processor(text=text, return_tensors="pt")
            with torch.no_grad():
                waveform = self._model.generate_speech(
                    inputs["input_ids"],
                    self._speaker_embeddings,
                    vocoder=self._vocoder,
                )
            pcm = (waveform.numpy() * 32_767).clip(-32_768, 32_767).astype(np.int16)
            segment = AudioSegment(
                pcm.tobytes(), frame_rate=SAMPLE_RATE, sample_width=2, channels=1
            )
            combined += segment
            pause_ms = (
                self.paragraph_pause_ms if is_paragraph_end else self.sentence_pause_ms
            )
            combined += AudioSegment.silent(duration=pause_ms, frame_rate=SAMPLE_RATE)

        if len(combined) == 0:
            raise ValueError("sentences list produced no audio — all entries were blank")

        combined.export(str(output_path), format="mp3", bitrate="128k")
        return output_path
