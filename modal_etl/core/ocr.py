import base64
import io
import json
from pathlib import Path

from modal_etl.core.ollama import call_ollama_generate

OLLAMA_TIMEOUT = 600

PAGASA_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "bulletin_type": {"type": "string", "enum": ["SWB", "TCA", "TCB", "other"]},
        "bulletin_number": {"type": ["integer", "null"]},
        "storm": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "former_name": {"type": ["string", "null"]},
                "international_name": {"type": ["string", "null"]},
                "category": {
                    "type": "string",
                    "enum": [
                        "Tropical Depression",
                        "Tropical Storm",
                        "Severe Tropical Storm",
                        "Typhoon",
                        "Super Typhoon",
                    ],
                },
                "wind_signal": {"type": ["integer", "null"]},
            },
            "required": ["name", "category"],
        },
        "issuance": {
            "type": "object",
            "properties": {
                "datetime": {"type": ["string", "null"]},
                "valid_until": {"type": ["string", "null"]},
            },
        },
        "current_position": {
            "type": "object",
            "properties": {
                "latitude": {"type": ["number", "null"]},
                "longitude": {"type": ["number", "null"]},
                "reference": {"type": ["string", "null"]},
                "as_of": {"type": ["string", "null"]},
            },
        },
        "intensity": {
            "type": "object",
            "properties": {
                "max_sustained_winds_kph": {"type": ["integer", "null"]},
                "gusts_kph": {"type": ["integer", "null"]},
            },
        },
        "movement": {
            "type": "object",
            "properties": {
                "direction": {"type": ["string", "null"]},
                "speed_kph": {"type": ["integer", "null"]},
            },
        },
        "wind_extent": {"type": ["string", "null"]},
        "land_hazards": {"type": ["string", "null"]},
        "track_outlook": {"type": ["string", "null"]},
        "forecast_positions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "hour": {"type": "integer"},
                    "label": {"type": "string"},
                    "latitude": {"type": ["number", "null"]},
                    "longitude": {"type": ["number", "null"]},
                    "reference": {"type": ["string", "null"]},
                },
                "required": ["hour", "label"],
            },
        },
        "affected_areas": {
            "type": "object",
            "properties": {
                "signal_1": {"type": "array", "items": {"type": "string"}},
                "signal_2": {"type": "array", "items": {"type": "string"}},
                "signal_3": {"type": "array", "items": {"type": "string"}},
                "signal_4": {"type": "array", "items": {"type": "string"}},
                "signal_5": {"type": "array", "items": {"type": "string"}},
                "rainfall_warning": {"type": "array", "items": {"type": "string"}},
                "coastal_waters": {"type": ["string", "null"]},
            },
        },
        "storm_track_map": {
            "type": "object",
            "properties": {
                "current_position_shown": {"type": "boolean"},
                "forecast_track_shown": {"type": "boolean"},
                "description": {"type": ["string", "null"]},
            },
        },
        "headline": {"type": ["string", "null"]},
        "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
    },
    "required": [
        "bulletin_type",
        "storm",
        "issuance",
        "current_position",
        "intensity",
        "movement",
        "forecast_positions",
        "affected_areas",
        "storm_track_map",
        "confidence",
    ],
}

_NARRATIVE_SYSTEM_PROMPT = (
    "You are an expert OCR assistant for PAGASA Philippine weather bulletins issued by "
    "the Philippine Atmospheric, Geophysical and Astronomical Services Administration.\n\n"
    "Extract ONLY the following fields from the bulletin pages. "
    "Output clean Markdown preserving headings and lists.\n\n"
    "FIELDS TO EXTRACT:\n"
    "- Bulletin type and number\n"
    "- Storm current name, former name (if any), international name (if any)\n"
    "- Issue date and time\n"
    "- Headline (the short all-caps summary line, "
    "e.g. '\"VERBENA\" WEAKENS WHILE MOVING WEST SOUTHWESTWARD SLOWLY')\n"
    "- Location of Center (coordinates + reference landmark + as-of time)\n"
    "- Intensity (max sustained winds + gusts in km/h)\n"
    "- Present Movement (direction + speed)\n"
    "- Extent of Tropical Cyclone Winds (narrative, "
    "e.g. 'Winds of at least 30 km/h extend outward up to 280 km from the center')\n"
    "- Tropical Cyclone Wind Signals in Effect (list of areas per signal level)\n"
    "- Other Hazards Affecting Land Areas (rainfall advisory, storm surge, flooding)\n"
    "- Hazards Affecting Coastal Waters\n"
    "- Track and Intensity Outlook (narrative forecast summary paragraph)\n"
    "- Storm track map: describe what you see — storm position, forecast track, "
    "affected regions, symbols and legend items\n\n"
    "DO NOT EXTRACT: The 'Track and Intensity Forecast' table. "
    "It appears at the bottom of page 1 as a multi-column table with rows labeled "
    "'12-Hour Forecast', '24-Hour Forecast', etc. "
    "Stop before it and do not read any of its contents."
)

_NARRATIVE_USER = (
    "Extract all narrative bulletin fields and describe the storm track map "
    "from this PAGASA typhoon bulletin image. Do not include the forecast table."
)

_FORECAST_TABLE_SYSTEM_PROMPT = (
    "You are a precise data-extraction assistant specialising in PAGASA typhoon bulletins.\n\n"
    "Your ONLY task is to extract the Track and Intensity Forecast table from the provided bulletin image.\n\n"
    "TABLE LOCATION: The table is in the LOWER HALF of the page, below the two-column section "
    "(which has narrative text on the left and a storm track map on the right). "
    "The table header row reads: TRACK AND INTENSITY FORECAST.\n\n"
    "TABLE STRUCTURE — extract exactly these columns:\n"
    "| Date and Time | Lat. (°N) | Lon. (°E) | Location | MSW (km/h) | Cat. | "
    "Movement dir. and speed (km/h) |\n\n"
    "ROWS: The table always has exactly 8 forecast rows labeled:\n"
    "12-Hour Forecast (Time and Date), 24-Hour Forecast (Time and Date), 36-Hour Forecast (Time and Date), 48-Hour Forecast (Time and Date), "
    "60-Hour Forecast (Time and Date), 72-Hour Forecast (Time and Date), 96-Hour Forecast (Time and Date), 120-Hour Forecast (Time and Date).\n\n"
    "RULES:\n"
    "- Output ONLY the Markdown table. No preamble, no explanation, no other text.\n"
    "- Copy values exactly as printed — do NOT round, correct, or interpolate.\n"
    "- If a cell is not legible, output an empty cell (||) — never guess.\n"
    "- The Date and Time cell spans two lines (e.g. '12-Hour Forecast\\n8:00 AM\\n04 December 2025'). "
    "Combine onto one line separated by spaces.\n"
    "- Cat. values are abbreviations: LPA, TD, TS, STS, TY, STY.\n"
    "- Movement values are compass direction + speed (e.g. 'WSW 20', 'W Slowly', 'Stationary')."
)

_FORECAST_TABLE_USER = (
    "Extract the Track and Intensity Forecast table from this PAGASA bulletin page. "
    "Output only the Markdown table."
)

_METADATA_SYSTEM_PROMPT = (
    "You are PAGASAParseAI, an expert at converting extracted PAGASA typhoon bulletin text into structured JSON.\n\n"
    "Extract only the fields listed in the schema. Do not include full_text or any free-form text dump.\n\n"
    "CRITICAL RULES:\n"
    "- Output ONLY the JSON object. No preamble, no markdown fences, no explanation.\n"
    "- If a field cannot be determined, use null or an empty array. Never hallucinate.\n"
    "- forecast_positions must include every position shown (24h, 48h, 72h, 96h, 120h).\n"
    "- FORMER NAME: If a former/previous name is mentioned, extract it into the former_name field. "
    "Otherwise set former_name to null. Current storm name can be empty or null if not found.\n"
    "- HEADLINE: Extract the short all-caps summary line that appears near the top of the bulletin "
    "(e.g. '\"VERBENA\" WEAKENS WHILE MOVING WEST SOUTHWESTWARD SLOWLY'). "
    "It is typically found in the Remarks or General Remarks section. "
    "Capture it exactly as written including any quotation marks around the storm name. "
    "If not present, set headline to null.\n\n"
    "NEW FIELDS — extract these if present in the bulletin text:\n"
    "- wind_extent: narrative string describing how far cyclone winds extend outward "
    "(e.g. 'Winds of at least 30 km/h extend outward up to 280 km from the center'). "
    "Set null if not stated.\n"
    "- land_hazards: narrative string covering rainfall advisories, storm surge warnings, "
    "and flooding warnings for land areas. Set null if none.\n"
    "- track_outlook: the Track and Intensity Outlook narrative paragraph. "
    "Set null if not present."
)


def _pdf_to_pil_pages(pdf_bytes: bytes, dpi: int = 200):
    from pdf2image import convert_from_bytes
    return convert_from_bytes(pdf_bytes, dpi=dpi)


def _page_to_b64(pil_image) -> str:
    buf = io.BytesIO()
    pil_image.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def _extract_forecast_table(page1, ollama_url: str, model: str) -> str:
    """Run a focused second pass on page 1 to extract the forecast table accurately."""
    img_b64 = _page_to_b64(page1)
    return call_ollama_generate(
        url=ollama_url,
        model=model,
        prompt=_FORECAST_TABLE_USER,
        system=_FORECAST_TABLE_SYSTEM_PROMPT,
        images_b64=[img_b64],
        timeout=OLLAMA_TIMEOUT,
    ).strip()


def _extract_narrative(pages, ollama_url: str, model: str) -> str:
    pages_md = []
    for i, page in enumerate(pages):
        img_b64 = _page_to_b64(page)
        page_md = call_ollama_generate(
            url=ollama_url,
            model=model,
            prompt=_NARRATIVE_USER,
            system=_NARRATIVE_SYSTEM_PROMPT,
            images_b64=[img_b64],
            timeout=OLLAMA_TIMEOUT,
        )
        pages_md.append(f"<!-- Page {i + 1} -->\n\n{page_md}")
    return "\n\n---\n\n".join(pages_md)


def _find_chart_page(pages, ollama_url: str, model: str) -> int:
    all_b64 = [_page_to_b64(p) for p in pages]
    prompt = (
        f"This PAGASA weather bulletin has {len(pages)} pages (0-indexed: "
        f"0 to {len(pages) - 1}). "
        "Which page contains the storm track map or weather disturbance chart? "
        "Reply with a single integer — the 0-based page index only. No explanation."
    )
    response = call_ollama_generate(
        url=ollama_url,
        model=model,
        prompt=prompt,
        images_b64=all_b64,
        timeout=OLLAMA_TIMEOUT,
    ).strip()
    try:
        idx = int(response.split()[0])
        return max(0, min(idx, len(pages) - 1))
    except (ValueError, IndexError):
        return len(pages) - 1


def _generate_metadata(
    markdown: str,
    ollama_url: str,
    model: str,
    forecast_table_md: str | None = None,
) -> dict:
    if forecast_table_md:
        prompt = (
            "Here is the extracted text from a PAGASA bulletin:\n\n"
            f"{markdown}\n\n"
            "---\n\n"
            "IMPORTANT: For the forecast_positions field, use ONLY the following verified table "
            "(ignore any forecast data in the text above — this table is more accurate):\n\n"
            f"{forecast_table_md}\n\n"
            "Convert this into the structured JSON schema."
        )
    else:
        prompt = (
            "Here is the extracted text from a PAGASA bulletin:\n\n"
            f"{markdown}\n\n"
            "Convert this into the structured JSON schema."
        )
    raw = call_ollama_generate(
        url=ollama_url,
        model=model,
        prompt=prompt,
        system=_METADATA_SYSTEM_PROMPT,
        fmt=PAGASA_JSON_SCHEMA,
        timeout=OLLAMA_TIMEOUT,
    )
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"[run_step1] metadata JSON parse failed: {exc}\nRaw output: {raw[:500]}") from exc


def run_step1(
    pdf_path: Path,
    output_dir: Path,
    ollama_url: str = "http://localhost:11434",
    model: str = "gemma4:e4b",
    force: bool = False,
    stem: str | None = None,
) -> Path:
    """Run OCR on pdf_path and write ocr.md, chart.png, metadata.json to output_dir/{stem}/.

    Returns:
        Path to the stem-scoped output directory (output_dir/{stem}/).
    """
    stem = stem or pdf_path.stem
    out_dir = output_dir / stem
    ocr_path = out_dir / "ocr.md"
    forecast_table_path = out_dir / "forecast_table.md"
    chart_path = out_dir / "chart.png"
    metadata_path = out_dir / "metadata.json"

    if (
        ocr_path.exists()
        and forecast_table_path.exists()
        and chart_path.exists()
        and metadata_path.exists()
        and not force
    ):
        print(f"[run_step1] {stem}: all outputs exist, skipping")
        return out_dir

    out_dir.mkdir(parents=True, exist_ok=True)
    pdf_bytes = pdf_path.read_bytes()
    pages = _pdf_to_pil_pages(pdf_bytes)

    if not ocr_path.exists() or force:
        markdown = _extract_narrative(pages, ollama_url, model)
        ocr_path.write_text(markdown, encoding="utf-8")
        print(f"[run_step1] {stem}: wrote ocr.md ({len(markdown)} chars)")
    else:
        markdown = ocr_path.read_text(encoding="utf-8")

    if not forecast_table_path.exists() or force:
        forecast_table_md = _extract_forecast_table(pages[0], ollama_url, model)
        forecast_table_path.write_text(forecast_table_md, encoding="utf-8")
        print(f"[run_step1] {stem}: wrote forecast_table.md ({len(forecast_table_md)} chars)")
    else:
        forecast_table_md = forecast_table_path.read_text(encoding="utf-8")

    if not chart_path.exists() or force:
        chart_idx = _find_chart_page(pages, ollama_url, model)
        pages[chart_idx].save(str(chart_path), format="PNG")
        print(f"[run_step1] {stem}: saved chart.png (page {chart_idx})")

    if not metadata_path.exists() or force:
        metadata = _generate_metadata(markdown, ollama_url, model, forecast_table_md)
        metadata_path.write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"[run_step1] {stem}: wrote metadata.json")

    return out_dir
