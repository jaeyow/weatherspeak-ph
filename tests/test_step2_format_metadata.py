"""Tests for _format_metadata_for_prompt in step2_scripts."""

import pytest
from modal_etl.step2_scripts import _format_metadata_for_prompt


VERBENA_METADATA = {
    "bulletin_type": "TCB",
    "bulletin_number": 24,
    "storm": {
        "name": "VERBENA",
        "international_name": "KOTO",
        "category": "Typhoon",
        "wind_signal": None,
    },
    "issuance": {
        "datetime": "2025-11-27 23:00:00",
        "valid_until": None,
    },
    "current_position": {
        "latitude": None,
        "longitude": None,
        "reference": "270 km Northwest of Pag-asa Island, Kalayaan, Palawan (OUTSIDE PAR)",
        "as_of": None,
    },
    "intensity": {
        "max_sustained_winds_kph": 120,
        "gusts_kph": 150,
    },
    "movement": {
        "direction": "West-Southwest",
        "speed_kph": None,
    },
    "forecast_positions": [
        {
            "hour": 24,
            "label": "24-Hour Forecast",
            "latitude": 13.0,
            "longitude": 112.1,
            "reference": "320 km Northwest of Pag-asa Island (OUTSIDE PAR)",
        },
    ],
    "affected_areas": {
        "signal_1": [],
        "signal_2": [],
        "signal_3": [],
        "signal_4": [],
        "signal_5": [],
        "rainfall_warning": [],
        "coastal_waters": None,
    },
    "storm_track_map": {"description": "Track moves northwest away from Philippines."},
    "confidence": 1.0,
}

SIGNAL_METADATA = {
    "bulletin_type": "TCB",
    "bulletin_number": 3,
    "storm": {
        "name": "PEPITO",
        "international_name": None,
        "category": "Typhoon",
        "wind_signal": 3,
    },
    "issuance": {
        "datetime": "2025-10-21 05:00:00",
        "valid_until": "2025-10-21 11:00:00",
    },
    "current_position": {
        "latitude": 15.0,
        "longitude": 124.5,
        "reference": "50 km East of Catanduanes",
        "as_of": None,
    },
    "intensity": {
        "max_sustained_winds_kph": 150,
        "gusts_kph": 185,
    },
    "movement": {
        "direction": "West-Northwest",
        "speed_kph": 20,
    },
    "forecast_positions": [
        {
            "hour": 12,
            "label": "12-Hour Forecast",
            "latitude": 15.2,
            "longitude": 123.0,
            "reference": "Over Catanduanes",
        },
    ],
    "affected_areas": {
        "signal_1": ["Aurora", "Quezon"],
        "signal_2": ["Camarines Norte", "Camarines Sur"],
        "signal_3": ["Catanduanes", "Albay"],
        "signal_4": [],
        "signal_5": [],
        "rainfall_warning": ["Eastern Samar"],
        "coastal_waters": "Rough seas over Bicol coastal waters.",
    },
    "storm_track_map": {"description": "Track crosses Luzon heading northwest."},
    "confidence": 0.9,
}


# ── Storm identity ───────────────────────────────────────────────────────────

def test_storm_name_present():
    result = _format_metadata_for_prompt(VERBENA_METADATA)
    assert "VERBENA" in result


def test_storm_category_present():
    result = _format_metadata_for_prompt(VERBENA_METADATA)
    assert "Typhoon" in result


def test_international_name_present():
    result = _format_metadata_for_prompt(VERBENA_METADATA)
    assert "KOTO" in result


def test_bulletin_number_present():
    result = _format_metadata_for_prompt(VERBENA_METADATA)
    assert "24" in result


def test_issuance_datetime_present():
    result = _format_metadata_for_prompt(VERBENA_METADATA)
    assert "2025-11-27" in result


# ── Position and intensity ───────────────────────────────────────────────────

def test_current_position_reference_present():
    result = _format_metadata_for_prompt(VERBENA_METADATA)
    assert "270 km Northwest of Pag-asa Island" in result


def test_outside_par_flagged():
    result = _format_metadata_for_prompt(VERBENA_METADATA)
    assert "OUTSIDE PAR" in result or "outside" in result.lower()


def test_wind_speed_labelled():
    result = _format_metadata_for_prompt(VERBENA_METADATA)
    assert "120" in result
    assert "WIND" in result.upper() or "wind" in result


def test_gusts_present():
    result = _format_metadata_for_prompt(VERBENA_METADATA)
    assert "150" in result


def test_movement_direction_present():
    result = _format_metadata_for_prompt(VERBENA_METADATA)
    assert "West-Southwest" in result


def test_movement_speed_null_handled():
    result = _format_metadata_for_prompt(VERBENA_METADATA)
    assert result  # non-empty, no crash


def test_movement_speed_present_when_available():
    result = _format_metadata_for_prompt(SIGNAL_METADATA)
    assert "20" in result


# ── No-signal / outside PAR case ────────────────────────────────────────────

def test_no_signals_clearly_stated():
    result = _format_metadata_for_prompt(VERBENA_METADATA)
    lower = result.lower()
    assert "no wind signal" in lower or "none" in lower or "no signal" in lower


# ── Signal areas ─────────────────────────────────────────────────────────────

def test_signal_1_areas_present():
    result = _format_metadata_for_prompt(SIGNAL_METADATA)
    assert "Aurora" in result
    assert "Quezon" in result


def test_signal_3_areas_present():
    result = _format_metadata_for_prompt(SIGNAL_METADATA)
    assert "Catanduanes" in result
    assert "Albay" in result


def test_rainfall_warning_areas_present():
    result = _format_metadata_for_prompt(SIGNAL_METADATA)
    assert "Eastern Samar" in result


def test_coastal_waters_present():
    result = _format_metadata_for_prompt(SIGNAL_METADATA)
    assert "Rough seas" in result


# ── Forecast track ───────────────────────────────────────────────────────────

def test_forecast_positions_present():
    result = _format_metadata_for_prompt(VERBENA_METADATA)
    assert "24" in result


def test_forecast_reference_present():
    result = _format_metadata_for_prompt(VERBENA_METADATA)
    assert "320 km Northwest" in result


# ── Next bulletin ─────────────────────────────────────────────────────────────

def test_valid_until_when_present():
    result = _format_metadata_for_prompt(SIGNAL_METADATA)
    assert "2025-10-21 11:00:00" in result


def test_valid_until_when_null():
    result = _format_metadata_for_prompt(VERBENA_METADATA)
    assert result  # no crash when valid_until is None
