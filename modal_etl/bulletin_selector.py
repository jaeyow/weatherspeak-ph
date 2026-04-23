import re
import requests
from dataclasses import dataclass
from urllib.parse import quote
from modal_etl.config import ARCHIVE_API_URL, ARCHIVE_RAW_BASE


@dataclass
class BulletinInfo:
    stem: str          # filename without .pdf
    pdf_url: str       # raw GitHub download URL
    event_name: str    # storm name (e.g. "Pepito")
    storm_id: str      # e.g. "20-19W" or "22-TC02"
    bulletin_seq: int  # sequence number (#NN)


_FILENAME_RE = re.compile(
    r"^PAGASA_([^_]+)_([A-Za-z]+)_(?:SWB|TCA|TCB|TCW)#(\d+)\.pdf$"
)


def parse_bulletin_filename(filename: str) -> BulletinInfo | None:
    """Parse a PAGASA bulletin filename. Returns None if not a valid bulletin."""
    name = filename.split("/")[-1]  # strip any directory prefix
    m = _FILENAME_RE.match(name)
    if not m:
        return None
    storm_id, event_name, seq_str = m.group(1), m.group(2), m.group(3)
    stem = name[: -len(".pdf")]
    return BulletinInfo(
        stem=stem,
        pdf_url="",  # filled in by get_latest_bulletins
        event_name=event_name,
        storm_id=storm_id,
        bulletin_seq=int(seq_str),
    )


def group_by_event(bulletins: list[BulletinInfo]) -> dict[str, list[BulletinInfo]]:
    """Group bulletins by storm event name."""
    groups: dict[str, list[BulletinInfo]] = {}
    for b in bulletins:
        groups.setdefault(b.event_name, []).append(b)
    return groups


def get_latest_bulletins(n: int) -> list[BulletinInfo]:
    """Return the latest bulletin for each of the newest N severe weather events.

    Recency is determined by storm_id lexicographic order (higher = more recent).
    """
    resp = requests.get(ARCHIVE_API_URL)
    resp.raise_for_status()
    tree = resp.json().get("tree", [])

    bulletins = []
    for node in tree:
        if node.get("type") != "blob":
            continue
        path = node["path"]
        info = parse_bulletin_filename(path)
        if info is None:
            continue
        # Build raw GitHub URL — encode # as %23 so it isn't treated as a fragment
        info.pdf_url = f"{ARCHIVE_RAW_BASE}/{quote(path, safe='/')}"
        bulletins.append(info)

    groups = group_by_event(bulletins)

    # Pick latest bulletin per event
    latest_per_event: list[BulletinInfo] = []
    for event_bulletins in groups.values():
        latest = max(event_bulletins, key=lambda b: b.bulletin_seq)
        latest_per_event.append(latest)

    # Sort events by storm_id descending (lexicographic — higher = more recent)
    latest_per_event.sort(key=lambda b: b.storm_id, reverse=True)

    return latest_per_event[:n]


def get_all_bulletins_for_storm(storm_id: str, event_name: str) -> list[BulletinInfo]:
    """Return ALL bulletins for a specific storm event, sorted by bulletin_seq ascending.

    Args:
        storm_id:   Archive storm identifier, e.g. "20-19W" or "22-TC02".
                    This is the second underscore-segment of the filename,
                    e.g. from "PAGASA_20-19W_Pepito_SWB#01.pdf".
        event_name: Storm name, e.g. "Pepito" or "Basyang".
    """
    resp = requests.get(ARCHIVE_API_URL)
    resp.raise_for_status()
    tree = resp.json().get("tree", [])

    bulletins = []
    for node in tree:
        if node.get("type") != "blob":
            continue
        path = node["path"]
        info = parse_bulletin_filename(path)
        if info is None:
            continue
        if info.storm_id != storm_id or info.event_name != event_name:
            continue
        info.pdf_url = f"{ARCHIVE_RAW_BASE}/{quote(path, safe='/')}"
        bulletins.append(info)

    bulletins.sort(key=lambda b: b.bulletin_seq)
    return bulletins
