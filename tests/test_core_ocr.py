"""Tests for modal_etl/core/ocr.py — skip logic and path handling only (no Ollama/PIL)."""
import json
import pytest
from pathlib import Path
from modal_etl.core.ocr import run_step1, PAGASA_JSON_SCHEMA


def _write_all_step1_outputs(stem_dir: Path) -> None:
    (stem_dir / "ocr.md").write_text("# OCR content", encoding="utf-8")
    (stem_dir / "chart.png").write_bytes(b"fakepng")
    (stem_dir / "metadata.json").write_text('{"bulletin_type": "TCA"}', encoding="utf-8")


def test_run_step1_skips_when_all_outputs_exist(tmp_path):
    """run_step1 returns stem_dir immediately when all outputs exist and force=False."""
    stem = "PAGASA_TEST"
    pdf_path = tmp_path / f"{stem}.pdf"
    pdf_path.write_bytes(b"fake pdf")
    stem_dir = tmp_path / stem
    stem_dir.mkdir()
    _write_all_step1_outputs(stem_dir)

    result = run_step1(pdf_path, tmp_path, force=False)

    assert result == stem_dir


def test_run_step1_uses_stem_override(tmp_path):
    """run_step1 uses the stem parameter instead of pdf_path.stem when provided."""
    pdf_path = tmp_path / "irrelevant_name.pdf"
    pdf_path.write_bytes(b"fake pdf")
    custom_stem = "PAGASA_22-TC02_Basyang_TCA#01"
    stem_dir = tmp_path / custom_stem
    stem_dir.mkdir()
    _write_all_step1_outputs(stem_dir)

    result = run_step1(pdf_path, tmp_path, stem=custom_stem, force=False)

    assert result == stem_dir


def test_run_step1_force_reruns_even_when_outputs_exist(tmp_path, monkeypatch):
    """run_step1 with force=True calls _ocr_pdf even when outputs already exist."""
    stem = "PAGASA_TEST"
    pdf_path = tmp_path / f"{stem}.pdf"
    pdf_path.write_bytes(b"fake pdf")
    stem_dir = tmp_path / stem
    stem_dir.mkdir()
    _write_all_step1_outputs(stem_dir)

    called = []

    class FakePage:
        def save(self, path, format): pass

    monkeypatch.setattr("modal_etl.core.ocr._pdf_to_pil_pages", lambda b, dpi=200: [FakePage()])
    monkeypatch.setattr("modal_etl.core.ocr._ocr_pdf", lambda pages, url, model: (called.append(1), "# forced")[1])
    monkeypatch.setattr("modal_etl.core.ocr._find_chart_page", lambda pages, url, model: 0)
    monkeypatch.setattr("modal_etl.core.ocr._generate_metadata", lambda md, url, model: {"bulletin_type": "TCA", "storm": {"name": "T", "category": "Typhoon"}, "issuance": {}, "current_position": {}, "intensity": {}, "movement": {}, "forecast_positions": [], "affected_areas": {}, "storm_track_map": {}, "confidence": 1.0})

    run_step1(pdf_path, tmp_path, force=True)
    assert len(called) == 1


def test_pagasa_json_schema_has_required_fields():
    """PAGASA_JSON_SCHEMA defines all required top-level fields."""
    required = PAGASA_JSON_SCHEMA["required"]
    for field in ["bulletin_type", "storm", "issuance", "current_position",
                  "intensity", "movement", "forecast_positions", "affected_areas",
                  "storm_track_map", "confidence"]:
        assert field in required
