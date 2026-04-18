"""Step 4 — Upload ETL artifacts to Supabase Storage and write DB rows.

Reads from Modal output volume:
  /output/{stem}/chart.png
  /output/{stem}/audio_{lang}.mp3   (× 3)
  /output/{stem}/radio_{lang}.md    (× 3)
  /output/{stem}/metadata.json

Writes to Supabase Storage (weatherspeak-public bucket):
  charts/{stem}/chart.png
  audio/{stem}/audio_{lang}.mp3
  scripts/{stem}/radio_{lang}.md

Writes to Supabase DB:
  storms         — upsert (create if new storm)
  bulletins      — upsert on stem
  bulletin_media — upsert on (bulletin_id, language)

Skips upload if all three bulletin_media rows are already status='ready',
unless force=True.
"""

import json
import os
import re
from pathlib import Path
from urllib.parse import unquote

from modal_etl.app import app, upload_image, SUPABASE_SECRET, output_volume
from modal_etl.config import OUTPUT_PATH, LANGUAGES, STORAGE_BUCKET

# Stem format: PAGASA_{YY}-{storm_code}_{name}_{type}#{number}
_STEM_RE = re.compile(
    r"PAGASA_\d{2}-([^_]+)_([^_]+)_([^#]+)#(\d+)"
)

CONTENT_TYPES = {
    ".mp3": "audio/mpeg",
    ".md":  "text/markdown; charset=utf-8",
    ".png": "image/png",
}


def _parse_stem(stem: str) -> dict:
    """Extract storm_code, storm_name, bulletin_type, bulletin_number from stem."""
    m = _STEM_RE.match(stem)
    if not m:
        raise ValueError(f"Cannot parse stem: {stem!r}")
    return {
        "storm_code":      m.group(1),   # "19W" or "TC02"
        "storm_name":      m.group(2),   # "Pepito"
        "bulletin_type":   m.group(3),   # "SWB"
        "bulletin_number": int(m.group(4)),
    }


def _parse_issued_at(raw: str | None) -> str | None:
    """Parse a PAGASA datetime string to ISO 8601. Returns None on failure."""
    if not raw:
        return None
    try:
        from dateutil import parser as dtparser
        dt = dtparser.parse(raw, dayfirst=False)
        if dt.tzinfo is None:
            import datetime
            dt = dt.replace(tzinfo=datetime.timezone(datetime.timedelta(hours=8)))
        return dt.isoformat()
    except Exception:
        return None


def _audio_duration(path: Path) -> int | None:
    """Return MP3 duration in whole seconds using mutagen."""
    try:
        from mutagen.mp3 import MP3
        return int(MP3(str(path)).info.length)
    except Exception:
        return None


def _upload_file(client, local_path: Path, storage_path: str) -> str:
    """Upload a file to Supabase Storage. Returns the storage_path."""
    data = local_path.read_bytes()
    suffix = local_path.suffix.lower()
    content_type = CONTENT_TYPES.get(suffix, "application/octet-stream")
    client.storage.from_(STORAGE_BUCKET).upload(
        path=storage_path,
        file=data,
        file_options={"content-type": content_type, "upsert": "true"},
    )
    return storage_path


@app.function(
    image=upload_image,
    volumes={str(OUTPUT_PATH): output_volume},
    secrets=[SUPABASE_SECRET],
    timeout=300,
)
def step4_upload(stem: str, force: bool = False) -> str:
    """Upload artifacts to Supabase Storage and write bulletin rows to DB.

    Args:
        stem:  Bulletin stem, e.g. "PAGASA_20-19W_Pepito_SWB#01".
        force: Re-upload and overwrite even if all media rows are ready.

    Returns:
        stem on success.
    """
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    client = create_client(supabase_url, supabase_key)

    # ------------------------------------------------------------------
    # Skip check
    # ------------------------------------------------------------------
    decoded_stem = unquote(stem)

    if not force:
        existing = (
            client.table("bulletin_media")
            .select("id, status, bulletins!inner(stem)")
            .eq("bulletins.stem", decoded_stem)
            .eq("status", "ready")
            .execute()
        )
        if len(existing.data) >= len(LANGUAGES):
            print(f"[Step4Upload] {decoded_stem}: all media ready, skipping")
            return stem

    # ------------------------------------------------------------------
    # Parse stem and load metadata
    # stem may arrive URL-encoded (e.g. %23 instead of #) from older runs.
    # decoded_stem is used for parsing, DB values, and Storage paths.
    # stem (original) is used only for Modal volume file lookups.
    # ------------------------------------------------------------------
    parsed = _parse_stem(decoded_stem)
    # Storage paths must not contain # (treated as URL fragment by browsers).
    storage_stem = decoded_stem.replace("#", "_")
    out_dir = OUTPUT_PATH / stem
    metadata_path = out_dir / "metadata.json"

    meta: dict = {}
    if metadata_path.exists():
        meta = json.loads(metadata_path.read_text(encoding="utf-8"))

    storm_meta   = meta.get("storm", {})
    issuance     = meta.get("issuance", {})
    position     = meta.get("current_position", {})
    intensity    = meta.get("intensity", {})
    movement     = meta.get("movement", {})

    # ------------------------------------------------------------------
    # Upsert storm row
    # ------------------------------------------------------------------
    storm_row = {
        "storm_code":         parsed["storm_code"],
        "storm_name":         parsed["storm_name"],
        "international_name": storm_meta.get("international_name"),
    }
    storm_result = (
        client.table("storms")
        .upsert(storm_row, on_conflict="storm_code,storm_name")
        .execute()
    )
    storm_id = storm_result.data[0]["id"]
    print(f"[Step4Upload] {decoded_stem}: storm_id={storm_id}")

    # ------------------------------------------------------------------
    # Upload chart
    # ------------------------------------------------------------------
    chart_path_local = out_dir / "chart.png"
    chart_storage_path = None
    if chart_path_local.exists():
        chart_storage_path = _upload_file(
            client, chart_path_local, f"{storage_stem}/chart.png"
        )
        print(f"[Step4Upload] {decoded_stem}: uploaded chart.png")

    # ------------------------------------------------------------------
    # Upsert bulletin row
    # ------------------------------------------------------------------

    # Normalize bulletin_type to enum value
    raw_type = parsed["bulletin_type"]
    btype = raw_type if raw_type in ("SWB", "TCA", "TCB") else "other"

    # Normalize category to enum value
    raw_cat = storm_meta.get("category", "")
    valid_categories = {
        "Tropical Depression", "Tropical Storm",
        "Severe Tropical Storm", "Typhoon", "Super Typhoon",
    }
    category = raw_cat if raw_cat in valid_categories else None

    bulletin_row = {
        "storm_id":                storm_id,
        "stem":                    decoded_stem,
        "bulletin_type":           btype,
        "bulletin_number":         parsed["bulletin_number"],
        "issued_at":               _parse_issued_at(issuance.get("datetime")),
        "valid_until":             _parse_issued_at(issuance.get("valid_until")),
        "category":                category,
        "wind_signal":             storm_meta.get("wind_signal"),
        "max_sustained_winds_kph": intensity.get("max_sustained_winds_kph"),
        "gusts_kph":               intensity.get("gusts_kph"),
        "movement_direction":      movement.get("direction"),
        "movement_speed_kph":      movement.get("speed_kph"),
        "current_lat":             position.get("latitude"),
        "current_lon":             position.get("longitude"),
        "current_reference":       position.get("reference"),
        "affected_areas":          meta.get("affected_areas"),
        "forecast_positions":      meta.get("forecast_positions"),
        "chart_path":              chart_storage_path,
        "pdf_url":                 meta.get("pdf_url"),
    }
    bulletin_result = (
        client.table("bulletins")
        .upsert(bulletin_row, on_conflict="stem")
        .execute()
    )
    bulletin_id = bulletin_result.data[0]["id"]
    print(f"[Step4Upload] {stem}: bulletin_id={bulletin_id}")

    # ------------------------------------------------------------------
    # Upload audio + scripts, upsert bulletin_media rows
    # ------------------------------------------------------------------
    for lang in LANGUAGES:
        audio_local  = out_dir / f"audio_{lang}.mp3"
        script_local = out_dir / f"radio_{lang}.md"
        tts_local    = out_dir / f"tts_{lang}.txt"

        audio_storage_path  = None
        script_storage_path = None
        tts_storage_path    = None
        duration = None
        status   = "failed"

        if audio_local.exists():
            audio_storage_path = _upload_file(
                client, audio_local, f"{storage_stem}/audio_{lang}.mp3"
            )
            duration = _audio_duration(audio_local)
            print(f"[Step4Upload] {decoded_stem}/{lang}: uploaded audio ({duration}s)")

        if script_local.exists():
            script_storage_path = _upload_file(
                client, script_local, f"{storage_stem}/radio_{lang}.md"
            )
            print(f"[Step4Upload] {decoded_stem}/{lang}: uploaded script")

        if tts_local.exists():
            tts_storage_path = _upload_file(
                client, tts_local, f"{storage_stem}/tts_{lang}.txt"
            )
            print(f"[Step4Upload] {decoded_stem}/{lang}: uploaded tts text")

        if audio_storage_path:
            status = "ready"

        media_row = {
            "bulletin_id":             bulletin_id,
            "language":                lang,
            "audio_path":              audio_storage_path,
            "script_path":             script_storage_path,
            "tts_path":                tts_storage_path,
            "audio_duration_seconds":  duration,
            "status":                  status,
        }
        client.table("bulletin_media").upsert(
            media_row, on_conflict="bulletin_id,language"
        ).execute()

    print(f"[Step4Upload] {decoded_stem}: done")
    return stem
