"""Tests for modal_etl/core/scripts.py — skip logic and _clean_ocr."""
import pytest
from pathlib import Path
from modal_etl.core.scripts import run_step2, _clean_ocr


def _write_step2_outputs(stem_dir: Path, lang: str) -> None:
    (stem_dir / f"radio_{lang}.md").write_text("# Radio script", encoding="utf-8")
    (stem_dir / f"tts_{lang}.txt").write_text("Plain text.", encoding="utf-8")


def test_run_step2_skips_when_outputs_exist(tmp_path):
    """run_step2 returns radio_path immediately when both outputs exist and force=False."""
    stem = "PAGASA_TEST"
    stem_dir = tmp_path / stem
    stem_dir.mkdir()
    (stem_dir / "ocr.md").write_text("# OCR", encoding="utf-8")
    (stem_dir / "metadata.json").write_text('{"bulletin_type": "TCA", "storm": {"name": "T", "category": "Typhoon"}}', encoding="utf-8")
    _write_step2_outputs(stem_dir, "en")

    result = run_step2(stem, "en", tmp_path, force=False)

    assert result == stem_dir / "radio_en.md"


def test_run_step2_raises_when_ocr_missing(tmp_path):
    """run_step2 raises FileNotFoundError when ocr.md does not exist."""
    stem = "PAGASA_TEST"
    stem_dir = tmp_path / stem
    stem_dir.mkdir()

    with pytest.raises(FileNotFoundError, match="ocr.md"):
        run_step2(stem, "en", tmp_path, force=False)


def test_clean_ocr_removes_bracket_placeholder_lines():
    """_clean_ocr strips lines that are entirely a [BRACKET LABEL]."""
    raw = "Normal text.\n[HEADER BLOCK]\nMore normal text."
    result = _clean_ocr(raw)
    assert "[HEADER BLOCK]" not in result
    assert "Normal text." in result
    assert "More normal text." in result


def test_clean_ocr_collapses_extra_blank_lines():
    """_clean_ocr collapses runs of 3+ blank lines to a single blank line."""
    raw = "Para one.\n\n\n\nPara two."
    result = _clean_ocr(raw)
    assert "\n\n\n" not in result


def test_clean_ocr_preserves_inline_brackets():
    """_clean_ocr does NOT strip [brackets] that appear mid-line."""
    raw = "Signal [1] areas include Catanduanes."
    result = _clean_ocr(raw)
    assert "Signal [1] areas include Catanduanes." in result
