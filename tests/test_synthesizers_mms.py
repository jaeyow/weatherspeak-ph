import pytest
import torch
import numpy as np
from pathlib import Path
from unittest.mock import MagicMock, patch
from pydub import AudioSegment

from modal_etl.synthesizers.mms import MMSSynthesizer
from modal_etl.synthesizers.base import TTSSynthesizer


def _mock_vits_model(num_samples: int = 8000, sample_rate: int = 16_000):
    mock = MagicMock()
    mock.return_value.waveform = torch.zeros(1, num_samples)
    mock.config.sampling_rate = sample_rate
    return mock


def _mock_tokenizer():
    mock = MagicMock()
    mock.return_value = {"input_ids": torch.tensor([[1, 2, 3]])}
    return mock


def _loaded_synthesizer(model_id: str = "facebook/mms-tts-ceb") -> MMSSynthesizer:
    """Return an MMSSynthesizer with mocked model/tokenizer already loaded."""
    synth = MMSSynthesizer(model_id)
    synth._model = _mock_vits_model()
    synth._tokenizer = _mock_tokenizer()
    return synth


def test_mms_synthesizer_satisfies_protocol():
    synth = MMSSynthesizer("facebook/mms-tts-ceb")
    assert isinstance(synth, TTSSynthesizer)


def test_mms_synthesize_creates_mp3(tmp_path):
    synth = _loaded_synthesizer()
    out = tmp_path / "out.mp3"
    synth.synthesize([("maayong buntag", True)], out)
    assert out.exists()
    assert out.stat().st_size > 0


def test_mms_synthesize_returns_output_path(tmp_path):
    synth = _loaded_synthesizer()
    out = tmp_path / "out.mp3"
    result = synth.synthesize([("maayong buntag", True)], out)
    assert result == out


def test_mms_synthesize_paragraph_pause_longer_than_sentence_pause(tmp_path):
    synth_s = _loaded_synthesizer()
    synth_p = _loaded_synthesizer()
    out_s = tmp_path / "sentence.mp3"
    out_p = tmp_path / "paragraph.mp3"
    synth_s.synthesize([("hello", False)], out_s)
    synth_p.synthesize([("hello", True)], out_p)
    dur_s = len(AudioSegment.from_mp3(str(out_s)))
    dur_p = len(AudioSegment.from_mp3(str(out_p)))
    assert dur_p > dur_s


def test_mms_synthesize_raises_on_empty_sentences(tmp_path):
    synth = _loaded_synthesizer()
    with pytest.raises(ValueError, match="empty"):
        synth.synthesize([], tmp_path / "out.mp3")


def test_mms_synthesize_two_sentences_longer_than_one(tmp_path):
    synth = _loaded_synthesizer()
    out1 = tmp_path / "one.mp3"
    out2 = tmp_path / "two.mp3"
    synth.synthesize([("hello", True)], out1)
    synth.synthesize([("hello", False), ("world", True)], out2)
    dur1 = len(AudioSegment.from_mp3(str(out1)))
    dur2 = len(AudioSegment.from_mp3(str(out2)))
    assert dur2 > dur1
