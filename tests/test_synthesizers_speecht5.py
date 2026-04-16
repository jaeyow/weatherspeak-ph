import pytest
import torch
import numpy as np
from pathlib import Path
from unittest.mock import MagicMock
from pydub import AudioSegment

from modal_etl.synthesizers.speecht5 import SpeechT5Synthesizer
from modal_etl.synthesizers.base import TTSSynthesizer

SAMPLE_RATE = 16_000


def _loaded_synthesizer() -> SpeechT5Synthesizer:
    """Return a SpeechT5Synthesizer with all internals mocked."""
    synth = SpeechT5Synthesizer()

    processor = MagicMock()
    processor.return_value = {"input_ids": torch.tensor([[1, 2, 3]])}

    model = MagicMock()
    waveform = torch.zeros(8000)
    model.generate_speech.return_value = waveform

    vocoder = MagicMock()

    synth._processor = processor
    synth._model = model
    synth._vocoder = vocoder
    synth._speaker_embeddings = torch.zeros(1, 512)
    return synth


def test_speecht5_satisfies_protocol():
    assert isinstance(SpeechT5Synthesizer(), TTSSynthesizer)


def test_speecht5_synthesize_creates_mp3(tmp_path):
    synth = _loaded_synthesizer()
    out = tmp_path / "out.mp3"
    synth.synthesize([("Tropical Depression Pepito.", True)], out)
    assert out.exists()
    assert out.stat().st_size > 0


def test_speecht5_synthesize_returns_output_path(tmp_path):
    synth = _loaded_synthesizer()
    out = tmp_path / "out.mp3"
    result = synth.synthesize([("Hello.", True)], out)
    assert result == out


def test_speecht5_synthesize_raises_on_empty(tmp_path):
    synth = _loaded_synthesizer()
    with pytest.raises(ValueError, match="empty"):
        synth.synthesize([], tmp_path / "out.mp3")


def test_speecht5_synthesize_raises_on_all_blank(tmp_path):
    synth = _loaded_synthesizer()
    with pytest.raises(ValueError, match="blank"):
        synth.synthesize([("   ", False), ("\t", True)], tmp_path / "out.mp3")


def test_speecht5_paragraph_pause_longer_than_sentence_pause(tmp_path):
    synth = _loaded_synthesizer()
    out_s = tmp_path / "sentence.mp3"
    out_p = tmp_path / "paragraph.mp3"
    synth.synthesize([("Hello.", False)], out_s)
    synth.synthesize([("Hello.", True)], out_p)
    assert len(AudioSegment.from_mp3(str(out_p))) > len(
        AudioSegment.from_mp3(str(out_s))
    )
