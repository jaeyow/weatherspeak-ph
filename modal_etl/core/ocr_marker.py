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
import re
from pathlib import Path
from typing import Any

from modal_etl.core.ocr import _generate_metadata
from modal_etl.core.ollama import call_ollama_generate

OLLAMA_TIMEOUT = 600


def _clean_marker_md(text: str) -> str:
    """Strip Marker artefacts that confuse the metadata extractor.

    Marker emits inline image references (![](...)) for logos, stamps, and
    embedded graphics. These lines add noise with no text value and cause the
    structured-output LLM to hallucinate or return null for real fields.
    """
    # Remove Markdown image references: ![](...) on their own line or inline
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)
    # Collapse runs of blank lines left behind
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

_CHART_DESCRIPTION_SYSTEM = (
    "You are an expert meteorological assistant analysing a PAGASA 'Track and Intensity Forecast' chart.\n\n"
    "You will receive: (1) the official PAGASA bulletin text — treat it as AUTHORITATIVE ground truth; "
    "(2) the storm track chart image — use it to confirm coordinates and geographic detail. "
    "When they conflict, defer to the bulletin text.\n\n"
    "Before the steps, read the bulletin and note the storm's current position, bearing, and whether it "
    "moves towards or away from the Philippines — these are your anchors throughout.\n\n"
    "STEP 1 — Anchor the Timeline\n"
    "  • Find the black header box (top centre): storm name + bulletin issue date/time = Reference Timestamp.\n"
    "  • Each timestamp label is linked to its track dot by a leader line — follow it to get exact coordinates.\n"
    "  • Identify the dot matching or close to the Reference Timestamp: that is the Current Position.\n\n"
    "STEP 2 — Sequence the Forecast\n"
    "  • Read every timestamp label on the track (form: '6PM 2 Dec. 2025 (Tue)'). Count them all.\n"
    "  • List ALL in chronological order with coordinates and Past/Future classification relative to the "
    "Reference Timestamp. Do not omit past ones — they confirm the current position dot is correct.\n"
    "  • The ordered Future timestamps are the forecast path.\n\n"
    "STEP 3 — Analyze Spatial Vector\n"
    "  • Compare Current Position to the LATEST future dot: longitude decrease → WEST, increase → EAST; "
    "latitude increase → NORTH, decrease → SOUTH. State the combined compass bearing.\n\n"
    "STEP 4 — Determine Proximity to the Philippines\n"
    "  • Philippine landmass ≈ 116°E–127°E. Longitude decreasing away from this range → Moving Away; "
    "Longitude increasing toward it → Moving Towards. State the verdict clearly.\n\n"
    "OUTPUT — exactly two sections, no other headings or text:\n\n"
    "### Storm Track Map Analysis\n"
    "[~200 words of flowing prose covering Steps 1–4. List each step's reasoning includingreference timestamp, current position coordinates, "
    "all timestamps with coordinates and Past/Future labels, compass bearing derivation, Towards/Away verdict]\n\n"
    "### Storm Track Map Outlook\n"
    "[~200 words of plain narrative for general audiences. "
    "LOCATION RULE: never write degrees or coordinates. "
    "Use the bulletin's own position descriptions (distance in km + direction + landmark name, "
    "e.g. '270 km Northwest of Pag-asa Island'). "
    "For forecast positions not named in the bulletin, describe by sea area and general direction "
    "(e.g. 'over the South China Sea, moving toward Vietnam'). "
    "Cover: storm name, current location, compass heading, Towards/Away verdict, "
    "geographic areas near each forecast position, intensity changes, wind signals.]"
)

_CHART_DESCRIPTION_USER_TMPL = (
    "OFFICIAL PAGASA BULLETIN TEXT:\n"
    "---\n"
    "{track_text}\n"
    "---\n\n"
    "Analyse the attached storm track chart using the bulletin above as ground truth. "
    "Work through Steps 1–4 then write the two required sections. "
    "Remember to not use any coordinates in the ### Storm Track Map Outlook\n."
)

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
    """Extract full text from all PDF pages and figures from page 1.

    Two-pass strategy:
    - Full PDF → Marker native path: accurate text and table extraction across
      all pages (no figure extraction needed here).
    - Page 1 PNG → Marker image path: visual bounding-box figure extraction to
      capture the storm track chart, which is a vector graphic on page 1 and
      would be missed by the PDF-native path.
    """
    import tempfile
    from pdf2image import convert_from_path
    from marker.output import text_from_rendered

    converter = _get_converter()

    # Pass 1: full PDF for complete text/table markdown across all pages
    rendered_full = converter(str(pdf_path))
    markdown, _, _ = text_from_rendered(rendered_full)

    # Pass 2: page 1 PNG for chart figure extraction
    pages = convert_from_path(str(pdf_path), dpi=200, first_page=1, last_page=1)
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        png_path = f.name
        pages[0].save(png_path, format="PNG")
    rendered_page1 = converter(png_path)
    _, _, figures = text_from_rendered(rendered_page1)

    return markdown, figures or {}


def _select_chart(figures: dict) -> Any | None:
    """Return the figure most likely to be the storm track chart.

    Filters out extreme banners (aspect < 0.2) and tiny images (< 100k px),
    then picks the largest by pixel area. Returns None if no figure passes —
    the caller falls back to the first PDF page in that case.
    """
    if not figures:
        return None
    images = list(figures.values())
    MIN_ASPECT = 0.2
    MIN_PIXELS = 100_000
    candidates = [
        img for img in images
        if img.size[1] / img.size[0] >= MIN_ASPECT and img.size[0] * img.size[1] >= MIN_PIXELS
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda img: img.size[0] * img.size[1])


_TRACK_SECTION_HEADINGS = (
    "track and intensity forecast",
    "track and intensity outlook",
    "intensity forecast",
    "track forecast",
)


def _extract_track_sections(markdown: str) -> str:
    """Extract Track and Intensity Forecast / Outlook sections from bulletin markdown.

    Scans for headings that match known PAGASA section names and returns all
    matching sections concatenated. Falls back to the full markdown if nothing
    is found so the caller always has something to work with.
    """
    import re
    sections: list[str] = []
    # Split on any markdown heading (# through ####)
    parts = re.split(r"(?m)^(#{1,4}\s+.+)$", markdown)
    i = 0
    while i < len(parts):
        chunk = parts[i]
        if re.match(r"^#{1,4}\s+", chunk):
            heading_text = re.sub(r"^#{1,4}\s+", "", chunk).strip().lower()
            body = parts[i + 1] if i + 1 < len(parts) else ""
            if any(kw in heading_text for kw in _TRACK_SECTION_HEADINGS):
                sections.append(chunk + "\n" + body)
            i += 2
        else:
            i += 1
    return "\n\n".join(sections).strip() if sections else markdown.strip()


def _describe_chart(chart_path: Path, ollama_url: str, model: str, track_text: str = "") -> str:
    """Run one Gemma 4 vision pass on chart_path, grounded by official bulletin text."""
    # print(f"[_describe_chart] track_text ({len(track_text)} chars):\n{'-'*60}\n{track_text or '(empty)'}\n{'-'*60}")
    img_b64 = base64.b64encode(chart_path.read_bytes()).decode("utf-8")
    prompt = _CHART_DESCRIPTION_USER_TMPL.format(
        track_text=track_text or "(no bulletin text available)"
    )
    return call_ollama_generate(
        url=ollama_url,
        model=model,
        prompt=prompt,
        system=_CHART_DESCRIPTION_SYSTEM,
        images_b64=[img_b64],
        timeout=OLLAMA_TIMEOUT,
        think=True,
    ).strip()


def run(
    pdf_path: Path,
    output_dir: Path,
    ollama_url: str = "http://localhost:11434",
    model: str = "gemma4:e4b",
    force: bool = False,
    stem: str | None = None,
) -> Path:
    """Run Marker OCR on pdf_path. Extracts all pages for text; page 1 PNG for chart figure.
    Writes ocr.md, chart.png, metadata.json to output_dir/{stem}/.

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
        track_text = _extract_track_sections(markdown)
        print(f"[run_step1_marker] {stem}: extracted {len(track_text)} chars of track/outlook text")
        # print(f"[run_step1_marker] {stem}: track_text content:\n{'-'*60}\n{track_text}\n{'-'*60}")
        chart_description = _describe_chart(chart_path, ollama_url, model, track_text=track_text)
        full_md = markdown + f"\n\n## Storm Track Map\n\nThe following is a written explanation of the storm track map chart image included in this bulletin.\n\n{chart_description}"
    else:
        print(f"[run_step1_marker] {stem}: no chart available")
        chart_path.write_bytes(b"")
        full_md = markdown

    ocr_path.write_text(full_md, encoding="utf-8")
    print(f"[run_step1_marker] {stem}: wrote ocr.md ({len(full_md)} chars)")

    # Step 3: Generate metadata from bulletin text only (no chart description, no image refs)
    # Passing full_md would include the appended Storm Track Map section and Marker image
    # references — both corrupt the structured-output extraction. Use clean bulletin text only.
    metadata = _generate_metadata(_clean_marker_md(markdown), ollama_url, model)
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[run_step1_marker] {stem}: wrote metadata.json")

    return out_dir
