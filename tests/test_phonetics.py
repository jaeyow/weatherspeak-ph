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
    assert "tro-pi-kal di-pre-syon" in result
    assert "Tropical Depression" not in result


@pytest.mark.parametrize("lang", ["tl", "ceb"])
def test_tropical_storm(lang):
    result = apply_phonetics("Tropical Storm Malakas", lang)
    assert "tro-pi-kal storm" in result
    assert "Tropical Storm" not in result


@pytest.mark.parametrize("lang", ["tl", "ceb"])
def test_severe_tropical_storm(lang):
    result = apply_phonetics("Severe Tropical Storm Pepito", lang)
    assert "se-beer tro-pi-kal storm" in result


@pytest.mark.parametrize("lang", ["tl", "ceb"])
def test_typhoon(lang):
    result = apply_phonetics("Typhoon Basyang", lang)
    assert "tai-pun" in result
    assert "Typhoon" not in result


@pytest.mark.parametrize("lang", ["tl", "ceb"])
def test_super_typhoon(lang):
    result = apply_phonetics("Super Typhoon Yolanda", lang)
    assert "su-per tai-pun" in result


# ---------------------------------------------------------------------------
# Directions
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("lang", ["tl", "ceb"])
def test_northeast(lang):
    result = apply_phonetics("moving northeast", lang)
    assert "nor-ist" in result
    assert "northeast" not in result


@pytest.mark.parametrize("lang", ["tl", "ceb"])
def test_northwest(lang):
    result = apply_phonetics("moving northwest", lang)
    assert "nor-west" in result


@pytest.mark.parametrize("lang", ["tl", "ceb"])
def test_northern(lang):
    result = apply_phonetics("Northern Luzon", lang)
    assert "nor-dern" in result
    assert "Northern" not in result


# ---------------------------------------------------------------------------
# Speed units
# ---------------------------------------------------------------------------

def test_kph_tagalog():
    result = apply_phonetics("winds of 130 kph", "tl")
    assert "ki-lo-me-tro ba-wat o-ras" in result
    assert "kph" not in result


def test_kph_cebuano():
    result = apply_phonetics("winds of 130 kph", "ceb")
    assert "ki-lo-me-tros sa usa ka oras" in result
    assert "kph" not in result


def test_kilometers_per_hour_tagalog():
    result = apply_phonetics("130 kilometers per hour", "tl")
    assert "ki-lo-me-tro ba-wat o-ras" in result


# ---------------------------------------------------------------------------
# Common weather / emergency terms
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("lang", ["tl", "ceb"])
def test_forecast(lang):
    result = apply_phonetics("forecast track", lang)
    assert "pore-kast" in result
    assert "forecast" not in result


@pytest.mark.parametrize("lang", ["tl", "ceb"])
def test_advisory(lang):
    result = apply_phonetics("weather advisory", lang)
    assert "ad-bay-so-ri" in result


@pytest.mark.parametrize("lang", ["tl", "ceb"])
def test_flashlight(lang):
    result = apply_phonetics("bring a flashlight", lang)
    assert "plash-layt" in result
    assert "flashlight" not in result


@pytest.mark.parametrize("lang", ["tl", "ceb"])
def test_coastal(lang):
    result = apply_phonetics("coastal areas", lang)
    assert "kos-tal" in result


@pytest.mark.parametrize("lang", ["tl", "ceb"])
def test_evacuation(lang):
    result = apply_phonetics("evacuation center", lang)
    assert "i-bak-yu-ey-syon" in result
    assert "sen-ter" in result


# ---------------------------------------------------------------------------
# Place names
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("lang", ["tl", "ceb"])
def test_luzon(lang):
    result = apply_phonetics("Northern Luzon", lang)
    assert "lu-son" in result
    assert "Luzon" not in result


@pytest.mark.parametrize("lang", ["tl", "ceb"])
def test_visayas(lang):
    result = apply_phonetics("Visayas region", lang)
    assert "bi-sa-yas" in result
    assert "Visayas" not in result


@pytest.mark.parametrize("lang", ["tl", "ceb"])
def test_mindanao(lang):
    result = apply_phonetics("parts of Mindanao", lang)
    assert "min-da-naw" in result


# ---------------------------------------------------------------------------
# Already-phonetic text is not double-converted
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("lang", ["tl", "ceb"])
def test_already_phonetic_untouched(lang):
    # "tro-pi-kal storm" contains no raw English words — should be unchanged
    text = "ang tro-pi-kal storm ay malakas"
    assert apply_phonetics(text, lang) == text


# ---------------------------------------------------------------------------
# PAGASA name
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("lang", ["tl", "ceb"])
def test_pagasa_all_caps(lang):
    result = apply_phonetics("PAGASA issued a warning", lang)
    assert "pag-asa" in result


@pytest.mark.parametrize("lang", ["tl", "ceb"])
def test_pagasa_hyphenated(lang):
    result = apply_phonetics("PAG-ASA issued a warning", lang)
    assert "pag-asa" in result
