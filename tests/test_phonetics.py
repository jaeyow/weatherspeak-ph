"""Tests for modal_etl.phonetics.apply_phonetics."""

import pytest
from modal_etl.phonetics import apply_phonetics


# ---------------------------------------------------------------------------
# English passthrough
# ---------------------------------------------------------------------------

def test_english_unchanged():
    text = "Tropical Storm Pepito is moving northwest at 15 kph."
    assert apply_phonetics(text, "en") == text


def test_unknown_language_unchanged():
    text = "Tropical Storm Pepito"
    assert apply_phonetics(text, "xx") == text


# ---------------------------------------------------------------------------
# Storm categories
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("lang", ["tl", "ceb"])
def test_tropical_depression(lang):
    result = apply_phonetics("Tropical Depression Pepito", lang)
    assert "tro pi kal di pre syon" in result
    assert "Tropical Depression" not in result


@pytest.mark.parametrize("lang", ["tl", "ceb"])
def test_tropical_storm(lang):
    result = apply_phonetics("Tropical Storm Malakas", lang)
    assert "tro pi kal storm" in result
    assert "Tropical Storm" not in result


@pytest.mark.parametrize("lang", ["tl", "ceb"])
def test_severe_tropical_storm(lang):
    result = apply_phonetics("Severe Tropical Storm Pepito", lang)
    assert "se beer tro pi kal storm" in result


@pytest.mark.parametrize("lang", ["tl", "ceb"])
def test_typhoon(lang):
    result = apply_phonetics("Typhoon Basyang", lang)
    assert "tai pun" in result
    assert "Typhoon" not in result


@pytest.mark.parametrize("lang", ["tl", "ceb"])
def test_super_typhoon(lang):
    result = apply_phonetics("Super Typhoon Yolanda", lang)
    assert "su per tai pun" in result


# ---------------------------------------------------------------------------
# Directions
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("lang", ["tl", "ceb"])
def test_northeast(lang):
    result = apply_phonetics("moving northeast", lang)
    assert "nor ist" in result
    assert "northeast" not in result


@pytest.mark.parametrize("lang", ["tl", "ceb"])
def test_northwest(lang):
    result = apply_phonetics("moving northwest", lang)
    assert "nor west" in result


@pytest.mark.parametrize("lang", ["tl", "ceb"])
def test_northern(lang):
    result = apply_phonetics("Northern Luzon", lang)
    assert "nor dern" in result
    assert "Northern" not in result


# ---------------------------------------------------------------------------
# Speed units
# ---------------------------------------------------------------------------

def test_kph_tagalog():
    result = apply_phonetics("winds of 130 kph", "tl")
    assert "ki lo me tro ba wat o ras" in result
    assert "kph" not in result


def test_kph_cebuano():
    result = apply_phonetics("winds of 130 kph", "ceb")
    assert "ki lo me tros sa usa ka oras" in result
    assert "kph" not in result


def test_kilometers_per_hour_tagalog():
    result = apply_phonetics("130 kilometers per hour", "tl")
    assert "ki lo me tro ba wat o ras" in result


# ---------------------------------------------------------------------------
# Common weather / emergency terms
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("lang", ["tl", "ceb"])
def test_forecast(lang):
    result = apply_phonetics("forecast track", lang)
    assert "pore kast" in result
    assert "forecast" not in result


@pytest.mark.parametrize("lang", ["tl", "ceb"])
def test_advisory(lang):
    result = apply_phonetics("weather advisory", lang)
    assert "ad bay so ri" in result


@pytest.mark.parametrize("lang", ["tl", "ceb"])
def test_flashlight(lang):
    result = apply_phonetics("bring a flashlight", lang)
    assert "plash layt" in result
    assert "flashlight" not in result


@pytest.mark.parametrize("lang", ["tl", "ceb"])
def test_coastal(lang):
    result = apply_phonetics("coastal areas", lang)
    assert "kos tal" in result


@pytest.mark.parametrize("lang", ["tl", "ceb"])
def test_evacuation(lang):
    result = apply_phonetics("evacuation center", lang)
    assert "i bak yu ey syon" in result
    assert "sen ter" in result


# ---------------------------------------------------------------------------
# Place names
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("lang", ["tl", "ceb"])
def test_luzon(lang):
    result = apply_phonetics("Northern Luzon", lang)
    assert "lu son" in result
    assert "Luzon" not in result


@pytest.mark.parametrize("lang", ["tl", "ceb"])
def test_visayas(lang):
    result = apply_phonetics("Visayas region", lang)
    assert "bi sa yas" in result
    assert "Visayas" not in result


@pytest.mark.parametrize("lang", ["tl", "ceb"])
def test_mindanao(lang):
    result = apply_phonetics("parts of Mindanao", lang)
    assert "min da naw" in result


# ---------------------------------------------------------------------------
# Already-phonetic text is not double-converted
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("lang", ["tl", "ceb"])
def test_already_phonetic_untouched(lang):
    # "tro pi kal storm" contains no raw English words — should be unchanged
    text = "ang tro pi kal storm ay malakas"
    assert apply_phonetics(text, lang) == text


# ---------------------------------------------------------------------------
# PAGASA name
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("lang", ["tl", "ceb"])
def test_pagasa_all_caps(lang):
    result = apply_phonetics("PAGASA issued a warning", lang)
    assert "pag asa" in result


@pytest.mark.parametrize("lang", ["tl", "ceb"])
def test_pagasa_hyphenated(lang):
    result = apply_phonetics("PAG-ASA issued a warning", lang)
    assert "pag asa" in result


# ---------------------------------------------------------------------------
# PAGASA full name components
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("lang", ["tl", "ceb"])
def test_geophysical(lang):
    result = apply_phonetics("Geophysical and Astronomical Services Administration", lang)
    assert "dyi o pi si kal" in result
    assert "as tro nom i kal" in result
    assert "ser bi ses" in result
    assert "ad mi nis trey syon" in result


# ---------------------------------------------------------------------------
# Pressure / meteorological units
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("lang", ["tl", "ceb"])
def test_low_pressure_area(lang):
    result = apply_phonetics("Low Pressure Area", lang)
    assert "low pre shur e ri ya" in result
    assert "Low Pressure Area" not in result


@pytest.mark.parametrize("lang", ["tl", "ceb"])
def test_lpa(lang):
    result = apply_phonetics("now classified as LPA", lang)
    assert "el pi ey" in result
    assert "LPA" not in result


@pytest.mark.parametrize("lang", ["tl", "ceb"])
def test_hpa(lang):
    result = apply_phonetics("central pressure of 1004 hPa", lang)
    assert "ek to pas kal" in result
    assert "hPa" not in result


# ---------------------------------------------------------------------------
# Weather / action terms added in second pass
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("lang", ["tl", "ceb"])
def test_flash_flood(lang):
    result = apply_phonetics("risk of flash floods", lang)
    assert "plash plud" in result
    assert "flash flood" not in result


@pytest.mark.parametrize("lang", ["tl", "ceb"])
def test_low_lying(lang):
    result = apply_phonetics("low-lying areas", lang)
    assert "low lay ing" in result


@pytest.mark.parametrize("lang", ["tl", "ceb"])
def test_weakened(lang):
    result = apply_phonetics("the system has weakened", lang)
    assert "wi ken" in result
    assert "weakened" not in result


@pytest.mark.parametrize("lang", ["tl", "ceb"])
def test_secure(lang):
    result = apply_phonetics("secure loose objects", lang)
    assert "si kyur" in result


@pytest.mark.parametrize("lang", ["tl", "ceb"])
def test_secure_with_prefix(lang):
    # Filipino verb prefix "i-secure" — "secure" part should still convert
    result = apply_phonetics("i-secure ang mga butang", lang)
    assert "si kyur" in result


@pytest.mark.parametrize("lang", ["tl", "ceb"])
def test_monitor(lang):
    result = apply_phonetics("monitor the situation", lang)
    assert "mo ni tor" in result


@pytest.mark.parametrize("lang", ["tl", "ceb"])
def test_summary(lang):
    result = apply_phonetics("here is a summary", lang)
    assert "sa ma ri" in result
