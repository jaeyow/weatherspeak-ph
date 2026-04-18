import numpy as np
import torch
from pathlib import Path
from pydub import AudioSegment


class MMSSynthesizer:
    """TTS synthesizer backed by facebook/mms-tts-* VITS models.

    Requires lowercase, punctuation-stripped input (MMS hard requirement).
    Use prepare_mms_sentences() from step3_tts.py to prepare input.
    """

    def __init__(
        self,
        model_id: str,
        cache_dir: Path | None = None,
        sentence_pause_ms: int = 250,
        paragraph_pause_ms: int = 400,
        speech_speed: float = 1.15,
    ):
        self.model_id = model_id
        self.cache_dir = cache_dir
        self.sentence_pause_ms = sentence_pause_ms
        self.paragraph_pause_ms = paragraph_pause_ms
        self.speech_speed = speech_speed
        self._model = None
        self._tokenizer = None
        self._device = None

    def load(self) -> None:
        """Load VITS model and tokenizer onto GPU if available, otherwise CPU."""
        from transformers import VitsModel, AutoTokenizer
        self._device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"[MMSSynthesizer] loading {self.model_id} on {self._device}")
        self._tokenizer = AutoTokenizer.from_pretrained(
            self.model_id, cache_dir=self.cache_dir
        )
        self._model = VitsModel.from_pretrained(
            self.model_id, cache_dir=self.cache_dir
        ).to(self._device)

    def synthesize(
        self,
        sentences: list[tuple[str, bool]],
        output_path: Path,
    ) -> Path:
        """Synthesize sentences to MP3 with silence stitching.

        Args:
            sentences: list of (text, is_paragraph_end) — must be lowercase,
                       punctuation-stripped (MMS hard requirement).
            output_path: destination MP3 path.

        Returns:
            output_path on success.
        """
        if not sentences:
            raise ValueError("sentences list is empty — nothing to synthesize")

        rate = self._model.config.sampling_rate
        combined = AudioSegment.empty()

        for text, is_paragraph_end in sentences:
            if not text.strip():
                continue
            inputs = self._tokenizer(text, return_tensors="pt")
            inputs = {k: v.to(self._device) for k, v in inputs.items()}
            with torch.no_grad():
                waveform = self._model(**inputs).waveform
            pcm = (
                waveform.squeeze().cpu().numpy() * 32_767
            ).clip(-32_768, 32_767).astype(np.int16)

            segment = AudioSegment(
                pcm.tobytes(), frame_rate=rate, sample_width=2, channels=1
            )

            # Speed via frame-rate resampling (avoids pydub speedup artefacts)
            if self.speech_speed != 1.0:
                new_rate = int(rate * self.speech_speed)
                segment = segment._spawn(
                    segment.raw_data, overrides={"frame_rate": new_rate}
                ).set_frame_rate(rate)

            combined += segment
            pause_ms = (
                self.paragraph_pause_ms if is_paragraph_end else self.sentence_pause_ms
            )
            combined += AudioSegment.silent(duration=pause_ms, frame_rate=rate)

        if len(combined) == 0:
            raise ValueError("sentences list produced no audio — all entries were blank")

        combined.export(str(output_path), format="mp3", bitrate="128k")
        return output_path
