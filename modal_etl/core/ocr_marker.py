"""Marker-based OCR backend for PAGASA typhoon bulletins.

Replaces the two-pass Gemma 4 OCR with:
  1. Marker PDF extraction → full markdown (text + tables natively accurate)
  2. Largest extracted figure → chart.png
  3. One Gemma 4 vision pass on chart.png → storm track description appended to ocr.md
  4. Shared _generate_metadata() → metadata.json

Does NOT produce forecast_table.md — Marker's table extraction is accurate enough
that the metadata LLM can read the table directly from ocr.md.
"""
from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any

from modal_etl.core.ocr import _generate_metadata
from modal_etl.core.ollama import call_ollama_generate

OLLAMA_TIMEOUT = 600

_CHART_DESCRIPTION_SYSTEM = (
    "You are an expert on PAGASA Philippine weather bulletin storm track maps. "
    "Describe what you see in one concise paragraph: the storm's current position, "
    "the forecast track direction, affected regions, and any legend items or symbols visible."
)

_CHART_DESCRIPTION_USER = "Describe this PAGASA storm track map image. Some images may have \
    the map embedded in the page layout rather than as a separate figure; do your best to describe \
    the storm track based on the visual information available."

_converter: Any = None


def _get_converter() -> Any:
    """Load Marker PdfConverter once; cache at module level for reuse."""
    global _converter
    if _converter is None:
        from marker.converters.pdf import PdfConverter
        from marker.config.parser import ConfigParser
        from marker.models import create_model_dict

        config_parser = ConfigParser(
            {
                "output_format": "markdown",
                "langs": ["English"],
                "disable_image_extraction": False,
            }
        )
        _converter = PdfConverter(
            artifact_dict=create_model_dict(),
            config=config_parser.generate_config_dict(),
            processor_list=config_parser.get_processors(),
            renderer=config_parser.get_renderer(),
        )
    return _converter


def _run_marker(pdf_path: Path) -> tuple[str, dict]:
    """Run Marker on the PDF. Returns (markdown_str, figures_dict)."""
    from marker.output import text_from_rendered

    converter = _get_converter()
    rendered = converter(str(pdf_path))
    markdown, _, figures = text_from_rendered(rendered)
    return markdown, figures or {}


def _select_chart(figures: dict) -> Any | None:
    """Return the figure most likely to be the storm track chart.

    Weather charts are square-ish. Filters to images with squareness >= 0.5
    (at most 2:1 in either dimension), then picks the largest by pixel area.
    Falls back to the overall largest if no image passes the squareness filter.
    """
    if not figures:
        return None
    images = list(figures.values())

    def squareness(img) -> float:
        w, h = img.size
        return min(w, h) / max(w, h)

    candidates = [img for img in images if squareness(img) >= 0.5]
    pool = candidates if candidates else images
    return max(pool, key=lambda img: img.size[0] * img.size[1])


def _describe_chart(chart_path: Path, ollama_url: str, model: str) -> str:
    """Run one Gemma 4 vision pass on chart_path and return a description string."""
    img_b64 = base64.b64encode(chart_path.read_bytes()).decode("utf-8")
    return call_ollama_generate(
        url=ollama_url,
        model=model,
        prompt=_CHART_DESCRIPTION_USER,
        system=_CHART_DESCRIPTION_SYSTEM,
        images_b64=[img_b64],
        timeout=OLLAMA_TIMEOUT,
    ).strip()


def run(
    pdf_path: Path,
    output_dir: Path,
    ollama_url: str = "http://localhost:11434",
    model: str = "gemma4:e4b",
    force: bool = False,
    stem: str | None = None,
) -> Path:
    """Run Marker OCR on pdf_path. Writes ocr.md, chart.png, metadata.json to output_dir/{stem}/.

    Does NOT write forecast_table.md — Marker handles tables accurately without a separate pass.

    Returns:
        Path to the stem-scoped output directory (output_dir/{stem}/).
    """
    stem = stem or pdf_path.stem
    out_dir = output_dir / stem
    ocr_path = out_dir / "ocr.md"
    chart_path = out_dir / "chart.png"
    metadata_path = out_dir / "metadata.json"

    if ocr_path.exists() and chart_path.exists() and metadata_path.exists() and not force:
        print(f"[run_step1_marker] {stem}: all outputs exist, skipping")
        return out_dir

    out_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: Extract text and figures
    markdown, figures = _run_marker(pdf_path)
    print(f"[run_step1_marker] {stem}: Marker extracted {len(markdown)} chars, {len(figures)} figures")

    # Step 2: Save chart and describe it
    chart_img = _select_chart(figures)
    
    # Fallback: If no suitable figure found, use first page as chart
    # (handles bulletins where map is embedded in page layout)
    if chart_img is None:
        print(f"[run_step1_marker] {stem}: no extractable figures, using first page as fallback")
        from pdf2image import convert_from_path
        pages = convert_from_path(str(pdf_path), first_page=1, last_page=1)
        if pages:
            chart_img = pages[0]
            print(f"[run_step1_marker] {stem}: extracted first page {chart_img.size[0]}x{chart_img.size[1]}")
    
    if chart_img is not None:
        chart_img.save(str(chart_path), format="PNG")
        print(f"[run_step1_marker] {stem}: saved chart.png")
        chart_description = _describe_chart(chart_path, ollama_url, model)
        full_md = markdown + f"\n\n## Storm Track Map\n\n{chart_description}"
    else:
        print(f"[run_step1_marker] {stem}: no chart available")
        chart_path.write_bytes(b"")
        full_md = markdown

    ocr_path.write_text(full_md, encoding="utf-8")
    print(f"[run_step1_marker] {stem}: wrote ocr.md ({len(full_md)} chars)")

    # Step 3: Generate metadata from full markdown (table included)
    metadata = _generate_metadata(full_md, ollama_url, model)
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[run_step1_marker] {stem}: wrote metadata.json")

    return out_dir
