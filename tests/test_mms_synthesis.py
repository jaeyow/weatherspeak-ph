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
    sentences: list[tuple[str, bool]],
    model,
    tokenizer,
    output_path: Path,
    sample_rate: int | None = None,
    sentence_pause_ms: int = 500,
    paragraph_pause_ms: int = 750,
) -> Path:
    """Synthesize sentences to MP3 using a HuggingFace VitsModel with silence stitching.

    Args:
        sentences: List of (sentence, is_paragraph_end) from prepare_mms_sentences().
        model: Loaded VitsModel instance.
        tokenizer: Loaded AutoTokenizer instance.
        output_path: Destination MP3 path.
        sample_rate: Override model's native sample rate if needed.
        sentence_pause_ms: Silence after each non-final sentence in a paragraph (ms).
        paragraph_pause_ms: Silence after the last sentence of each paragraph (ms).

    Returns:
        output_path on success.
    """
    rate = sample_rate or model.config.sampling_rate
    combined = AudioSegment.empty()
    for sentence, is_paragraph_end in sentences:
        if not sentence.strip():
            continue
        inputs = tokenizer(sentence, return_tensors="pt")
        with torch.no_grad():
            waveform = model(**inputs).waveform
        pcm = (waveform.squeeze().numpy() * 32_767).clip(-32_768, 32_767).astype(np.int16)
        segment = AudioSegment(pcm.tobytes(), frame_rate=rate, sample_width=2, channels=1)
        combined += segment
        pause_ms = paragraph_pause_ms if is_paragraph_end else sentence_pause_ms
        combined += AudioSegment.silent(duration=pause_ms, frame_rate=rate)
    combined.export(str(output_path), format="mp3", bitrate="128k")
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
        [("hello world", True)],
        _make_mock_model(),
        _make_mock_tokenizer(),
        output_path,
    )
    assert output_path.exists()


def test_synthesize_returns_output_path(tmp_path):
    output_path = tmp_path / "output.mp3"
    result = synthesize_with_mms(
        [("hello world", True)],
        _make_mock_model(),
        _make_mock_tokenizer(),
        output_path,
    )
    assert result == output_path


def test_synthesize_mp3_is_non_empty(tmp_path):
    output_path = tmp_path / "output.mp3"
    synthesize_with_mms(
        [("hello world", True)],
        _make_mock_model(num_samples=16_000),
        _make_mock_tokenizer(),
        output_path,
    )
    assert output_path.stat().st_size > 0


def test_synthesize_respects_sample_rate_override(tmp_path):
    """sample_rate kwarg overrides model.config.sampling_rate."""
    output_path = tmp_path / "output.mp3"
    result = synthesize_with_mms(
        [("test", True)],
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


def test_synthesize_paragraph_pause_longer_than_sentence_pause(tmp_path):
    """MP3 with paragraph pause (750ms) is longer than with sentence pause (500ms)."""
    sentence_path = tmp_path / "sentence.mp3"
    paragraph_path = tmp_path / "paragraph.mp3"
    mock_model = _make_mock_model(num_samples=8000)
    mock_tok = _make_mock_tokenizer()
    synthesize_with_mms(
        [("hello world", False)],
        mock_model,
        mock_tok,
        sentence_path,
        sentence_pause_ms=500,
        paragraph_pause_ms=750,
    )
    synthesize_with_mms(
        [("hello world", True)],
        mock_model,
        mock_tok,
        paragraph_path,
        sentence_pause_ms=500,
        paragraph_pause_ms=750,
    )
    sentence_dur = len(AudioSegment.from_mp3(str(sentence_path)))
    paragraph_dur = len(AudioSegment.from_mp3(str(paragraph_path)))
    assert paragraph_dur > sentence_dur


def test_synthesize_two_sentences_longer_than_one(tmp_path):
    """Two sentences produce a longer MP3 than one sentence."""
    one_path = tmp_path / "one.mp3"
    two_path = tmp_path / "two.mp3"
    mock_model = _make_mock_model(num_samples=8000)
    mock_tok = _make_mock_tokenizer()
    synthesize_with_mms(
        [("hello world", True)],
        mock_model,
        mock_tok,
        one_path,
    )
    synthesize_with_mms(
        [("hello world", False), ("goodbye world", True)],
        mock_model,
        mock_tok,
        two_path,
    )
    one_dur = len(AudioSegment.from_mp3(str(one_path)))
    two_dur = len(AudioSegment.from_mp3(str(two_path)))
    assert two_dur > one_dur
