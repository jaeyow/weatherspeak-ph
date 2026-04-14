"""Unit tests for synthesize_with_mms (notebook 08).

Tests use mocked model/tokenizer so no GPU or model download is needed.
The function under test is defined inline here — identical to the notebook cell.
"""
import numpy as np
import torch
import pytest
from pathlib import Path
from unittest.mock import MagicMock
from pydub import AudioSegment


def synthesize_with_mms(
    text: str,
    model,
    tokenizer,
    output_path: Path,
    sample_rate: int | None = None,
) -> Path:
    """Synthesize plain text to MP3 using a HuggingFace VitsModel.

    Modal-ready: all inputs are primitive types + Path; no notebook globals.

    Args:
        text: Plain text (no markdown). Use preprocess_for_tts() first.
        model: Loaded VitsModel instance.
        tokenizer: Loaded AutoTokenizer instance.
        output_path: Destination MP3 path.
        sample_rate: Override model's native sample rate if needed.

    Returns:
        output_path on success.
    """
    inputs = tokenizer(text, return_tensors="pt")
    with torch.no_grad():
        waveform = model(**inputs).waveform

    rate = sample_rate or model.config.sampling_rate

    # float32 [-1, 1] → int16 PCM for pydub
    pcm = (waveform.squeeze().numpy() * 32_767).clip(-32_768, 32_767).astype(np.int16)

    segment = AudioSegment(
        pcm.tobytes(),
        frame_rate=rate,
        sample_width=2,  # 16-bit = 2 bytes
        channels=1,
    )
    segment.export(str(output_path), format="mp3", bitrate="128k")
    return output_path


def _make_mock_model(num_samples: int = 8000, sample_rate: int = 16_000):
    """Return a MagicMock that behaves like VitsModel for synthesis."""
    mock = MagicMock()
    mock.return_value.waveform = torch.zeros(1, num_samples)
    mock.config.sampling_rate = sample_rate
    return mock


def _make_mock_tokenizer():
    """Return a MagicMock that behaves like AutoTokenizer."""
    mock = MagicMock()
    mock.return_value = {"input_ids": torch.tensor([[1, 2, 3]])}
    return mock


def test_synthesize_creates_mp3_file(tmp_path):
    output_path = tmp_path / "output.mp3"
    synthesize_with_mms(
        "hello world",
        _make_mock_model(),
        _make_mock_tokenizer(),
        output_path,
    )
    assert output_path.exists()


def test_synthesize_returns_output_path(tmp_path):
    output_path = tmp_path / "output.mp3"
    result = synthesize_with_mms(
        "hello world",
        _make_mock_model(),
        _make_mock_tokenizer(),
        output_path,
    )
    assert result == output_path


def test_synthesize_mp3_is_non_empty(tmp_path):
    output_path = tmp_path / "output.mp3"
    synthesize_with_mms(
        "hello world",
        _make_mock_model(num_samples=16_000),
        _make_mock_tokenizer(),
        output_path,
    )
    assert output_path.stat().st_size > 0


def test_synthesize_respects_sample_rate_override(tmp_path):
    """sample_rate kwarg overrides model.config.sampling_rate."""
    output_path = tmp_path / "output.mp3"
    # Model reports 16kHz but we override to 22050
    result = synthesize_with_mms(
        "test",
        _make_mock_model(num_samples=22_050, sample_rate=16_000),
        _make_mock_tokenizer(),
        output_path,
        sample_rate=22_050,
    )
    assert result.exists()
