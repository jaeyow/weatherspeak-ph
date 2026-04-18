import numpy as np
import pytest
from pathlib import Path
from unittest.mock import MagicMock
from pydub import AudioSegment

from modal_etl.synthesizers.xtts import CoquiXTTSSynthesizer, SAMPLE_RATE
from modal_etl.synthesizers.base import TTSSynthesizer


def _loaded_synthesizer() -> CoquiXTTSSynthesizer:
    """Return a CoquiXTTSSynthesizer with a mocked TTS model."""
    synth = CoquiXTTSSynthesizer()
    mock_tts = MagicMock()
    # tts() returns a list/array of floats — 1 second of silence
    mock_tts.tts.return_value = np.zeros(SAMPLE_RATE, dtype=np.float32)
    synth._tts = mock_tts
    return synth


def test_xtts_satisfies_protocol():
    assert isinstance(CoquiXTTSSynthesizer(), TTSSynthesizer)


def test_xtts_synthesize_creates_mp3(tmp_path):
    synth = _loaded_synthesizer()
    out = tmp_path / "out.mp3"
    synth.synthesize([("Good morning.", True)], out)
    assert out.exists()
    assert out.stat().st_size > 0


def test_xtts_synthesize_returns_output_path(tmp_path):
    synth = _loaded_synthesizer()
    out = tmp_path / "out.mp3"
    result = synth.synthesize([("Hello.", True)], out)
    assert result == out


def test_xtts_synthesize_raises_on_empty(tmp_path):
    synth = _loaded_synthesizer()
    with pytest.raises(ValueError, match="empty"):
        synth.synthesize([], tmp_path / "out.mp3")


def test_xtts_paragraph_pause_longer_than_sentence_pause(tmp_path):
    synth = _loaded_synthesizer()
    out_s = tmp_path / "sentence.mp3"
    out_p = tmp_path / "paragraph.mp3"
    synth.synthesize([("Hello.", False)], out_s)
    synth.synthesize([("Hello.", True)], out_p)
    assert len(AudioSegment.from_mp3(str(out_p))) > len(AudioSegment.from_mp3(str(out_s)))


def test_xtts_two_sentences_longer_than_one(tmp_path):
    synth = _loaded_synthesizer()
    out1 = tmp_path / "one.mp3"
    out2 = tmp_path / "two.mp3"
    synth.synthesize([("Hello.", True)], out1)
    synth.synthesize([("Hello.", False), ("World.", True)], out2)
    assert len(AudioSegment.from_mp3(str(out2))) > len(AudioSegment.from_mp3(str(out1)))
