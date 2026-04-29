"""Tests for modal_etl/core/ocr_marker.py — skip logic and output contract only."""
from pathlib import Path
import pytest


def _write_marker_outputs(stem_dir: Path) -> None:
    (stem_dir / "ocr.md").write_text("# OCR content", encoding="utf-8")
    (stem_dir / "chart.png").write_bytes(b"fakepng")
    (stem_dir / "metadata.json").write_text('{"bulletin_type": "TCA"}', encoding="utf-8")


def test_select_chart_prefers_chart_over_wide_banner():
    """A banner with more pixels is filtered by aspect ratio; the squarish chart wins."""
    from PIL import Image
    from modal_etl.core.ocr_marker import _select_chart

    banner = Image.new("RGB", (2000, 80))  # 160_000 px, aspect 0.04 < 0.2 → filtered
    chart = Image.new("RGB", (400, 350))   # 140_000 px, aspect 0.875 → passes
    result = _select_chart({"banner": banner, "chart": chart})
    assert result is chart


def test_select_chart_returns_none_when_all_filtered():
    """Returns None when no figures pass the aspect + size filters."""
    from PIL import Image
    from modal_etl.core.ocr_marker import _select_chart

    small = Image.new("RGB", (200, 150))   # 30_000 px < MIN_PIXELS → filtered
    banner = Image.new("RGB", (800, 30))   # aspect 0.038 < MIN_ASPECT → filtered
    result = _select_chart({"small": small, "banner": banner})
    assert result is None


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
