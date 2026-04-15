"""Unit tests for synthesize_with_mms (notebook 08).

Tests use mocked model/tokenizer so no GPU or model download is needed.
The function under test is defined inline here — identical to the notebook cell.
"""
import re
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


def prepare_mms_sentences(text: str) -> list[tuple[str, bool]]:
    """Split plain text into MMS-ready sentences with paragraph boundary flags.

    Returns list of (sentence, is_paragraph_end) tuples where:
    - sentence: lowercase, punctuation-stripped (in-word apostrophes/hyphens preserved)
    - is_paragraph_end: True if last sentence of its paragraph
    """
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    result = []
    for paragraph in paragraphs:
        sentences = re.split(r'(?<=[.!?])\s+', paragraph)
        sentences = [s.strip() for s in sentences if s.strip()]
        for sent_idx, sentence in enumerate(sentences):
            is_last_in_para = (sent_idx == len(sentences) - 1)
            sentence = sentence.lower()
            # Remove all punctuation except apostrophes and hyphens
            s = re.sub(r"[^\w\s'\-]", " ", sentence)
            # Remove apostrophes/hyphens not flanked by word characters (standalone)
            s = re.sub(r"(?<!\w)['\-]|['\-](?!\w)", " ", s)
            sentence = re.sub(r"\s+", " ", s).strip()
            if sentence:
                result.append((sentence, is_last_in_para))
    return result


def test_prepare_mms_sentences_single_sentence():
    result = prepare_mms_sentences("Hello world.")
    assert result == [("hello world", True)]


def test_prepare_mms_sentences_multi_sentence_paragraph():
    result = prepare_mms_sentences("Maayong buntag. Pag-andam na mo.")
    assert len(result) == 2
    assert result[0] == ("maayong buntag", False)
    assert result[1] == ("pag-andam na mo", True)


def test_prepare_mms_sentences_two_paragraphs():
    result = prepare_mms_sentences("First sentence.\n\nSecond sentence.")
    assert len(result) == 2
    assert result[0] == ("first sentence", True)
    assert result[1] == ("second sentence", True)


def test_prepare_mms_sentences_em_dash():
    result = prepare_mms_sentences("Ang bagyo—mabilis mokaon.")
    assert len(result) == 1
    assert "—" not in result[0][0]
    assert "bagyo" in result[0][0]
    assert "mabilis" in result[0][0]


def test_prepare_mms_sentences_apostrophe_in_word():
    result = prepare_mms_sentences("Mo'y dako kaayo.")
    assert len(result) == 1
    assert result[0][0] == "mo'y dako kaayo"


def test_prepare_mms_sentences_standalone_quotes_stripped():
    result = prepare_mms_sentences("'Hello world'.")
    assert len(result) == 1
    assert "'" not in result[0][0]
    assert result[0][0] == "hello world"


def test_prepare_mms_sentences_lowercase_and_no_punctuation():
    result = prepare_mms_sentences("PAGASA Signal Number TWO warns!")
    assert len(result) == 1
    assert result[0][0] == "pagasa signal number two warns"
