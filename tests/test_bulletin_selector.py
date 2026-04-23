# tests/test_bulletin_selector.py
import pytest
from unittest.mock import patch
from modal_etl.bulletin_selector import (
    parse_bulletin_filename,
    group_by_event,
    get_latest_bulletins,
    get_all_bulletins_for_storm,
    BulletinInfo,
)


# --- parse_bulletin_filename ---

def test_parse_swb_bulletin():
    info = parse_bulletin_filename("PAGASA_20-19W_Pepito_SWB#01.pdf")
    assert info is not None
    assert info.stem == "PAGASA_20-19W_Pepito_SWB#01"
    assert info.event_name == "Pepito"
    assert info.storm_id == "20-19W"
    assert info.bulletin_seq == 1


def test_parse_tca_bulletin():
    info = parse_bulletin_filename("PAGASA_22-TC02_Basyang_TCA#05.pdf")
    assert info is not None
    assert info.event_name == "Basyang"
    assert info.bulletin_seq == 5


def test_parse_returns_none_for_non_bulletin():
    assert parse_bulletin_filename("README.md") is None
    assert parse_bulletin_filename("PAGASA_random_garbage.pdf") is None


# --- group_by_event ---

def test_group_by_event_groups_same_storm():
    infos = [
        parse_bulletin_filename("PAGASA_20-19W_Pepito_SWB#01.pdf"),
        parse_bulletin_filename("PAGASA_20-19W_Pepito_SWB#02.pdf"),
        parse_bulletin_filename("PAGASA_22-TC02_Basyang_TCA#01.pdf"),
    ]
    groups = group_by_event(infos)
    assert "Pepito" in groups
    assert "Basyang" in groups
    assert len(groups["Pepito"]) == 2
    assert len(groups["Basyang"]) == 1


def test_group_by_event_latest_has_highest_seq():
    infos = [
        parse_bulletin_filename("PAGASA_20-19W_Pepito_SWB#01.pdf"),
        parse_bulletin_filename("PAGASA_20-19W_Pepito_SWB#03.pdf"),
        parse_bulletin_filename("PAGASA_20-19W_Pepito_SWB#02.pdf"),
    ]
    groups = group_by_event(infos)
    latest = max(groups["Pepito"], key=lambda b: b.bulletin_seq)
    assert latest.bulletin_seq == 3


# --- get_latest_bulletins (mocked GitHub API) ---

FAKE_TREE = {
    "tree": [
        {"path": "bulletins/PAGASA_20-19W_Pepito_SWB#01.pdf", "type": "blob"},
        {"path": "bulletins/PAGASA_20-19W_Pepito_SWB#02.pdf", "type": "blob"},
        {"path": "bulletins/PAGASA_22-TC02_Basyang_TCA#01.pdf", "type": "blob"},
        {"path": "README.md", "type": "blob"},
    ]
}


def test_get_latest_bulletins_returns_n_events():
    with patch("modal_etl.bulletin_selector.requests.get") as mock_get:
        mock_get.return_value.json.return_value = FAKE_TREE
        mock_get.return_value.raise_for_status = lambda: None
        results = get_latest_bulletins(n=2)
    assert len(results) == 2


def test_get_latest_bulletins_returns_latest_per_event():
    with patch("modal_etl.bulletin_selector.requests.get") as mock_get:
        mock_get.return_value.json.return_value = FAKE_TREE
        mock_get.return_value.raise_for_status = lambda: None
        results = get_latest_bulletins(n=10)
    pepito = next((r for r in results if "Pepito" in r.stem), None)
    assert pepito is not None
    assert pepito.bulletin_seq == 2  # latest, not #01


def test_get_latest_bulletins_pdf_url_is_raw_github():
    with patch("modal_etl.bulletin_selector.requests.get") as mock_get:
        mock_get.return_value.json.return_value = FAKE_TREE
        mock_get.return_value.raise_for_status = lambda: None
        results = get_latest_bulletins(n=10)
    for r in results:
        assert r.pdf_url.startswith("https://raw.githubusercontent.com")
        assert r.pdf_url.endswith(".pdf")


def test_get_latest_bulletins_hash_in_url_is_encoded():
    """# in bulletin filenames must be encoded as %23 or requests strips the fragment."""
    with patch("modal_etl.bulletin_selector.requests.get") as mock_get:
        mock_get.return_value.json.return_value = FAKE_TREE
        mock_get.return_value.raise_for_status = lambda: None
        results = get_latest_bulletins(n=10)
    for r in results:
        assert "#" not in r.pdf_url
        assert "%23" in r.pdf_url


# --- get_all_bulletins_for_storm ---

def test_get_all_bulletins_for_storm_returns_all_for_event():
    """Returns all bulletins for the requested storm, not just the latest."""
    with patch("modal_etl.bulletin_selector.requests.get") as mock_get:
        mock_get.return_value.json.return_value = FAKE_TREE
        mock_get.return_value.raise_for_status = lambda: None
        results = get_all_bulletins_for_storm("20-19W", "Pepito")
    assert len(results) == 2


def test_get_all_bulletins_for_storm_sorted_ascending():
    """Results are sorted by bulletin_seq ascending (oldest first)."""
    with patch("modal_etl.bulletin_selector.requests.get") as mock_get:
        mock_get.return_value.json.return_value = FAKE_TREE
        mock_get.return_value.raise_for_status = lambda: None
        results = get_all_bulletins_for_storm("20-19W", "Pepito")
    seqs = [r.bulletin_seq for r in results]
    assert seqs == sorted(seqs)


def test_get_all_bulletins_for_storm_excludes_other_storms():
    """Does not include bulletins for a different storm."""
    with patch("modal_etl.bulletin_selector.requests.get") as mock_get:
        mock_get.return_value.json.return_value = FAKE_TREE
        mock_get.return_value.raise_for_status = lambda: None
        results = get_all_bulletins_for_storm("20-19W", "Pepito")
    stems = [r.stem for r in results]
    assert not any("Basyang" in s for s in stems)


def test_get_all_bulletins_for_storm_pdf_urls_encoded():
    """PDF URLs must not contain bare # characters."""
    with patch("modal_etl.bulletin_selector.requests.get") as mock_get:
        mock_get.return_value.json.return_value = FAKE_TREE
        mock_get.return_value.raise_for_status = lambda: None
        results = get_all_bulletins_for_storm("20-19W", "Pepito")
    for r in results:
        assert "#" not in r.pdf_url
        assert "%23" in r.pdf_url
        assert r.pdf_url.startswith("https://raw.githubusercontent.com")


def test_get_all_bulletins_for_storm_returns_empty_for_unknown():
    """Returns empty list when no bulletins match the requested storm."""
    with patch("modal_etl.bulletin_selector.requests.get") as mock_get:
        mock_get.return_value.json.return_value = FAKE_TREE
        mock_get.return_value.raise_for_status = lambda: None
        results = get_all_bulletins_for_storm("99-ZZ", "Unknown")
    assert results == []
