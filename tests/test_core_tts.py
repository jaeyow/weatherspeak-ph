"""Tests for modal_etl/core/tts.py — skip logic and error handling for run_step3."""
import pytest
from pathlib import Path
from modal_etl.core.tts import run_step3


def test_run_step3_skips_when_mp3_exists(tmp_path):
    """run_step3 returns mp3_path immediately when audio file exists and force=False."""
    stem = "PAGASA_TEST"
    stem_dir = tmp_path / stem
    stem_dir.mkdir()
    (stem_dir / "tts_en.txt").write_text("Hello world.", encoding="utf-8")
    mp3_path = stem_dir / "audio_en.mp3"
    mp3_path.write_bytes(b"fake mp3")

    result = run_step3(stem, "en", tmp_path, tmp_path / "models", force=False)

    assert result == mp3_path


def test_run_step3_raises_for_unknown_language(tmp_path):
    """run_step3 raises ValueError for an unrecognised language code."""
    stem = "PAGASA_TEST"
    stem_dir = tmp_path / stem
    stem_dir.mkdir()
    (stem_dir / "tts_xx.txt").write_text("text", encoding="utf-8")

    with pytest.raises(ValueError, match="Unknown language"):
        run_step3(stem, "xx", tmp_path, tmp_path / "models", force=True)


def test_run_step3_raises_when_tts_text_missing(tmp_path):
    """run_step3 raises FileNotFoundError when tts_{lang}.txt does not exist."""
    stem = "PAGASA_TEST"
    stem_dir = tmp_path / stem
    stem_dir.mkdir()

    with pytest.raises(FileNotFoundError, match="tts_en.txt"):
        run_step3(stem, "en", tmp_path, tmp_path / "models", force=True)
