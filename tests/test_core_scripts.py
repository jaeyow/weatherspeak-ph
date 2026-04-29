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


def test_run_step2_tl_generates_en_first_if_missing(tmp_path, monkeypatch):
    """When radio_en.md is absent and language=tl, EN is generated first then TL is translated."""
    stem = "PAGASA_TEST"
    stem_dir = tmp_path / stem
    stem_dir.mkdir()
    (stem_dir / "ocr.md").write_text("Bulletin text.", encoding="utf-8")

    gen_calls: list[tuple] = []
    trans_calls: list[tuple] = []

    def fake_generate(ocr_md, language, ollama_url, model, metadata=None):
        gen_calls.append((ocr_md, language))
        return "English script"

    def fake_translate(english_md, language, ollama_url, model):
        trans_calls.append((english_md, language))
        return "Tagalog script"

    monkeypatch.setattr("modal_etl.core.scripts._generate_radio_script", fake_generate)
    monkeypatch.setattr("modal_etl.core.scripts._translate_radio_script", fake_translate)
    monkeypatch.setattr("modal_etl.core.scripts._generate_tts_text", lambda *a, **kw: "tts")
    monkeypatch.setattr("modal_etl.core.scripts._cleanup_english_words", lambda t, *a, **kw: t)
    monkeypatch.setattr("modal_etl.core.scripts._cleanup_numbers", lambda t, *a, **kw: t)

    result = run_step2(stem, "tl", tmp_path)

    assert len(gen_calls) == 1
    assert gen_calls[0][1] == "en"
    assert (stem_dir / "radio_en.md").read_text(encoding="utf-8") == "English script"
    assert len(trans_calls) == 1
    assert trans_calls[0] == ("English script", "tl")
    assert result == stem_dir / "radio_tl.md"
    assert (stem_dir / "radio_tl.md").read_text(encoding="utf-8") == "Tagalog script"


def test_run_step2_tl_uses_english_when_en_exists(tmp_path, monkeypatch):
    """When radio_en.md already exists, _translate_radio_script is called directly without generating EN."""
    stem = "PAGASA_TEST"
    stem_dir = tmp_path / stem
    stem_dir.mkdir()
    (stem_dir / "ocr.md").write_text("Bulletin text.", encoding="utf-8")
    (stem_dir / "radio_en.md").write_text("Pre-existing English script", encoding="utf-8")

    gen_calls: list = []
    trans_calls: list[tuple] = []

    def fake_generate(ocr_md, language, ollama_url, model, metadata=None):
        gen_calls.append(language)
        return "Regenerated English"

    def fake_translate(english_md, language, ollama_url, model):
        trans_calls.append((english_md, language))
        return "Tagalog from existing EN"

    monkeypatch.setattr("modal_etl.core.scripts._generate_radio_script", fake_generate)
    monkeypatch.setattr("modal_etl.core.scripts._translate_radio_script", fake_translate)
    monkeypatch.setattr("modal_etl.core.scripts._generate_tts_text", lambda *a, **kw: "tts")
    monkeypatch.setattr("modal_etl.core.scripts._cleanup_english_words", lambda t, *a, **kw: t)
    monkeypatch.setattr("modal_etl.core.scripts._cleanup_numbers", lambda t, *a, **kw: t)

    run_step2(stem, "tl", tmp_path)

    assert gen_calls == [], "Should NOT call _generate_radio_script when radio_en.md exists"
    assert len(trans_calls) == 1
    assert trans_calls[0] == ("Pre-existing English script", "tl")
    assert (stem_dir / "radio_tl.md").read_text(encoding="utf-8") == "Tagalog from existing EN"


def test_run_step2_en_path_unchanged(tmp_path, monkeypatch):
    """For language=en, _generate_radio_script is called and _translate_radio_script is never called."""
    stem = "PAGASA_TEST"
    stem_dir = tmp_path / stem
    stem_dir.mkdir()
    (stem_dir / "ocr.md").write_text("Bulletin text.", encoding="utf-8")

    gen_calls: list = []
    trans_calls: list = []

    def fake_generate(ocr_md, language, ollama_url, model, metadata=None):
        gen_calls.append(language)
        return "English script"

    def fake_translate(english_md, language, ollama_url, model):
        trans_calls.append(language)
        return "Should not be called"

    monkeypatch.setattr("modal_etl.core.scripts._generate_radio_script", fake_generate)
    monkeypatch.setattr("modal_etl.core.scripts._translate_radio_script", fake_translate)
    monkeypatch.setattr("modal_etl.core.scripts._generate_tts_text", lambda *a, **kw: "tts")
    monkeypatch.setattr("modal_etl.core.scripts._cleanup_english_words", lambda t, *a, **kw: t)
    monkeypatch.setattr("modal_etl.core.scripts._cleanup_numbers", lambda t, *a, **kw: t)

    run_step2(stem, "en", tmp_path)

    assert gen_calls == ["en"]
    assert trans_calls == [], "_translate_radio_script must not be called for language=en"


def test_run_step2_tl_force_regenerates_en(tmp_path, monkeypatch):
    """When force=True and radio_en.md already exists, EN is regenerated (not reused)."""
    stem = "PAGASA_TEST"
    stem_dir = tmp_path / stem
    stem_dir.mkdir()
    (stem_dir / "ocr.md").write_text("Bulletin text.", encoding="utf-8")
    (stem_dir / "radio_en.md").write_text("Stale English script", encoding="utf-8")

    gen_calls: list = []

    def fake_generate(ocr_md, language, ollama_url, model, metadata=None):
        gen_calls.append(language)
        return "Fresh English script"

    def fake_translate(english_md, language, ollama_url, model):
        return f"Translated from: {english_md}"

    monkeypatch.setattr("modal_etl.core.scripts._generate_radio_script", fake_generate)
    monkeypatch.setattr("modal_etl.core.scripts._translate_radio_script", fake_translate)
    monkeypatch.setattr("modal_etl.core.scripts._generate_tts_text", lambda *a, **kw: "tts")
    monkeypatch.setattr("modal_etl.core.scripts._cleanup_english_words", lambda t, *a, **kw: t)
    monkeypatch.setattr("modal_etl.core.scripts._cleanup_numbers", lambda t, *a, **kw: t)

    run_step2(stem, "tl", tmp_path, force=True)

    assert gen_calls == ["en"], "force=True must regenerate EN even when radio_en.md exists"
    assert (stem_dir / "radio_en.md").read_text(encoding="utf-8") == "Fresh English script"
    assert (stem_dir / "radio_tl.md").read_text(encoding="utf-8") == "Translated from: Fresh English script"
