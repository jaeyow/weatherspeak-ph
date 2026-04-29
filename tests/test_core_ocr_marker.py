"""Tests for modal_etl/core/ocr_marker.py — skip logic and output contract only."""
from pathlib import Path
import pytest


def _write_marker_outputs(stem_dir: Path) -> None:
    (stem_dir / "ocr.md").write_text("# OCR content", encoding="utf-8")
    (stem_dir / "chart.png").write_bytes(b"fakepng")
    (stem_dir / "metadata.json").write_text('{"bulletin_type": "TCA"}', encoding="utf-8")


def test_select_chart_prefers_chart_over_wide_banner():
    """A wide/short banner with more pixels than the chart should still lose."""
    from PIL import Image
    from modal_etl.core.ocr_marker import _select_chart

    banner = Image.new("RGB", (1200, 80))  # 96 000 px, ratio 0.067 — banner wins on area
    chart = Image.new("RGB", (300, 280))   # 84 000 px, ratio 0.933 — chart loses on area
    result = _select_chart({"banner": banner, "chart": chart})
    assert result is chart


def test_select_chart_falls_back_when_all_banners():
    """If every image is banner-shaped, return the largest by area."""
    from PIL import Image
    from modal_etl.core.ocr_marker import _select_chart

    small = Image.new("RGB", (400, 30))
    large = Image.new("RGB", (1000, 40))
    result = _select_chart({"small": small, "large": large})
    assert result is large


def test_select_chart_empty_returns_none():
    from modal_etl.core.ocr_marker import _select_chart
    assert _select_chart({}) is None


def test_run_marker_skips_when_outputs_exist(tmp_path):
    """run() returns stem_dir immediately when ocr.md, chart.png, metadata.json exist and force=False."""
    from modal_etl.core.ocr_marker import run

    stem = "PAGASA_TEST"
    pdf_path = tmp_path / f"{stem}.pdf"
    pdf_path.write_bytes(b"fake pdf")
    stem_dir = tmp_path / stem
    stem_dir.mkdir()
    _write_marker_outputs(stem_dir)

    result = run(pdf_path, tmp_path, force=False)

    assert result == stem_dir


def test_run_marker_force_reruns(tmp_path, monkeypatch):
    """run() with force=True calls _run_marker even when outputs already exist."""
    from modal_etl.core import ocr_marker
    from PIL import Image

    stem = "PAGASA_TEST"
    pdf_path = tmp_path / f"{stem}.pdf"
    pdf_path.write_bytes(b"fake pdf")
    stem_dir = tmp_path / stem
    stem_dir.mkdir()
    _write_marker_outputs(stem_dir)

    called = []
    fake_img = Image.new("RGB", (200, 200))

    monkeypatch.setattr(
        "modal_etl.core.ocr_marker._run_marker",
        lambda p: (called.append(1), ("# markdown", {"fig_0": fake_img}))[1],
    )
    monkeypatch.setattr(
        "modal_etl.core.ocr_marker._select_chart",
        lambda figs: fake_img,
    )
    monkeypatch.setattr(
        "modal_etl.core.ocr_marker._describe_chart",
        lambda path, url, model: "Storm is northwest of Palawan.",
    )
    monkeypatch.setattr(
        "modal_etl.core.ocr_marker._generate_metadata",
        lambda md, url, model, forecast_table_md=None: {
            "bulletin_type": "TCA",
            "storm": {"name": "TEST", "category": "Typhoon"},
            "issuance": {},
            "current_position": {},
            "intensity": {},
            "movement": {},
            "forecast_positions": [],
            "affected_areas": {},
            "storm_track_map": {},
            "confidence": 1.0,
        },
    )

    ocr_marker.run(pdf_path, tmp_path, force=True)

    assert len(called) == 1


def test_marker_does_not_produce_forecast_table_md(tmp_path, monkeypatch):
    """Marker mode never writes forecast_table.md."""
    from modal_etl.core import ocr_marker
    from PIL import Image

    stem = "PAGASA_TEST"
    pdf_path = tmp_path / f"{stem}.pdf"
    pdf_path.write_bytes(b"fake pdf")

    fake_img = Image.new("RGB", (200, 200))

    monkeypatch.setattr(
        "modal_etl.core.ocr_marker._run_marker",
        lambda p: ("# markdown", {"fig_0": fake_img}),
    )
    monkeypatch.setattr(
        "modal_etl.core.ocr_marker._select_chart",
        lambda figs: fake_img,
    )
    monkeypatch.setattr(
        "modal_etl.core.ocr_marker._describe_chart",
        lambda path, url, model: "Storm track description.",
    )
    monkeypatch.setattr(
        "modal_etl.core.ocr_marker._generate_metadata",
        lambda md, url, model, forecast_table_md=None: {
            "bulletin_type": "TCA",
            "storm": {"name": "TEST", "category": "Typhoon"},
            "issuance": {},
            "current_position": {},
            "intensity": {},
            "movement": {},
            "forecast_positions": [],
            "affected_areas": {},
            "storm_track_map": {},
            "confidence": 1.0,
        },
    )

    ocr_marker.run(pdf_path, tmp_path, force=True)

    stem_dir = tmp_path / stem
    assert (stem_dir / "ocr.md").exists()
    assert (stem_dir / "chart.png").exists()
    assert (stem_dir / "metadata.json").exists()
    assert not (stem_dir / "forecast_table.md").exists()
