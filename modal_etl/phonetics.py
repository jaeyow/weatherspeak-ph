"""Phonetic post-processing for PAGASA TTS text.

Gemma inconsistently applies phonetic spelling to English words in Tagalog and
Cebuano TTS text.  This module provides deterministic substitutions applied
*after* the LLM generates text so that MMS VITS models receive no raw English.

Rules:
- Patterns are applied in order: longest/most-specific first to avoid
  partial-word collisions (e.g. "Tropical Storm" before "Tropical").
- All matches are case-insensitive; replacements are lowercase phonetic forms.
- Word boundaries (\\b) prevent replacing already-phonetic substrings.
- Only applied to TL and CEB — English text is passed to XTTS v2 as-is.
"""

import re
from typing import NamedTuple


class Sub(NamedTuple):
    pattern: str
    replacement: str


# ---------------------------------------------------------------------------
# Shared substitutions (TL + CEB share most PAGASA vocabulary)
# ---------------------------------------------------------------------------

_COMMON: list[Sub] = [
    # PAGASA name -------------------------------------------------------
    Sub(r"\bPAGASA\b", "pag-asa"),
    Sub(r"\bPAG-ASA\b", "pag-asa"),

    # Storm categories — longest first to avoid "Tropical" matching before
    # the full phrase is consumed.
    Sub(r"\bsuper typhoon\b", "su-per tai-pun"),
    Sub(r"\bsevere tropical storm\b", "se-beer tro-pi-kal storm"),
    Sub(r"\btropical storm\b", "tro-pi-kal storm"),
    Sub(r"\btropical depression\b", "tro-pi-kal di-pre-syon"),
    Sub(r"\btropical cyclone\b", "tro-pi-kal say-klon"),
    Sub(r"\btyphoon\b", "tai-pun"),
    Sub(r"\btropical\b", "tro-pi-kal"),

    # Signal numbers — spell out digits and words -------------------------
    Sub(r"\bsignal\s+number\s+five\b", "sig-nal nam-ber payb"),
    Sub(r"\bsignal\s+number\s+four\b", "sig-nal nam-ber por"),
    Sub(r"\bsignal\s+number\s+three\b", "sig-nal nam-ber tri"),
    Sub(r"\bsignal\s+number\s+two\b", "sig-nal nam-ber tu"),
    Sub(r"\bsignal\s+number\s+one\b", "sig-nal nam-ber wan"),
    Sub(r"\bsignal\s+5\b", "sig-nal nam-ber payb"),
    Sub(r"\bsignal\s+4\b", "sig-nal nam-ber por"),
    Sub(r"\bsignal\s+3\b", "sig-nal nam-ber tri"),
    Sub(r"\bsignal\s+2\b", "sig-nal nam-ber tu"),
    Sub(r"\bsignal\s+1\b", "sig-nal nam-ber wan"),

    # Compass directions — compound before simple -------------------------
    Sub(r"\bnorth-?northeast\b", "nor-nor-ist"),
    Sub(r"\bnorth-?northwest\b", "nor-nor-west"),
    Sub(r"\bsouth-?southeast\b", "sow-sow-ist"),
    Sub(r"\bsouth-?southwest\b", "sow-sow-west"),
    Sub(r"\bnortheast\b", "nor-ist"),
    Sub(r"\bsoutheast\b", "sow-ist"),
    Sub(r"\bnorthwest\b", "nor-west"),
    Sub(r"\bsouthwest\b", "sow-west"),
    Sub(r"\bnorthward\b", "nor-ward"),
    Sub(r"\bsouthward\b", "sow-ward"),
    Sub(r"\beastward\b", "ist-ward"),
    Sub(r"\bwestward\b", "west-ward"),
    Sub(r"\bnorthern\b", "nor-dern"),
    Sub(r"\bsouthern\b", "sow-dern"),
    Sub(r"\beastern\b", "is-tern"),
    Sub(r"\bwestern\b", "wes-tern"),
    Sub(r"\bnorth\b", "nor"),
    Sub(r"\bsouth\b", "sow"),
    Sub(r"\beast\b", "ist"),
    # "west" is fine as-is for both TL and CEB phonemes — skip

    # Speed units ---------------------------------------------------------
    Sub(r"\bkilometers?\s+per\s+hour\b", "ki-lo-me-tro ba-wat o-ras"),
    Sub(r"\bkm/h\b", "ki-lo-me-tro ba-wat o-ras"),
    Sub(r"\bkph\b", "ki-lo-me-tro ba-wat o-ras"),
    Sub(r"\bkilometers?\b", "ki-lo-me-tro"),

    # PAGASA full name components -----------------------------------------
    Sub(r"\bGeophysical\b", "dyi-o-pi-si-kal"),
    Sub(r"\bAstronomical\b", "as-tro-nom-i-kal"),
    Sub(r"\bAtmospher(?:e|ic|ics)\b", "at-mos-pi-rik"),
    Sub(r"\bAdministration\b", "ad-mi-nis-trey-syon"),
    Sub(r"\bServices\b", "ser-bi-ses"),

    # Pressure / meteorological units -------------------------------------
    Sub(r"\bLow\s+Pressure\s+Area\b", "low pre-shur e-ri-ya"),
    Sub(r"\bLPA\b", "el pi-ey"),
    Sub(r"\bhPa\b", "ek-to-pas-kal"),
    Sub(r"\bpressure\b", "pre-shur"),
    Sub(r"\bcentral\b", "sen-tral"),

    # Common weather/emergency terms --------------------------------------
    Sub(r"\bforecast\b", "pore-kast"),
    Sub(r"\bbulletin\b", "bu-le-tin"),
    Sub(r"\badvisory\b", "ad-bay-so-ri"),
    Sub(r"\bwarning\b", "wor-ning"),
    Sub(r"\bupdate\b", "ap-deyt"),
    Sub(r"\bcoastal\b", "kos-tal"),
    Sub(r"\bcenter\b", "sen-ter"),
    Sub(r"\blandfall\b", "land-pol"),
    Sub(r"\brainfall\b", "reyn-pol"),
    Sub(r"\bstorm\s+surge\b", "storm serj"),
    Sub(r"\bsurge\b", "serj"),
    Sub(r"\bgust(?:y|s)?\b", "gast"),
    Sub(r"\bsustained\b", "sos-teyn-d"),
    Sub(r"\bintensif(?:y|ying|ied|ication)\b", "in-ten-si-pay"),
    Sub(r"\bintensity\b", "in-ten-si-ti"),
    Sub(r"\bweaken(?:ed|ing|s)?\b", "wi-ken"),
    Sub(r"\bflash\s+flood(?:s|ing)?\b", "plash plud"),
    Sub(r"\blow-lying\b", "low-lay-ing"),
    Sub(r"\btrack\b", "trak"),
    Sub(r"\bstatus\b", "sta-tus"),
    Sub(r"\bestimate\b", "es-ti-meyt"),
    Sub(r"\bsummary\b", "sa-ma-ri"),
    Sub(r"\bmonitor\b", "mo-ni-tor"),
    Sub(r"\bsecure\b", "si-kyur"),

    # Emergency preparedness words ----------------------------------------
    Sub(r"\bemergency\b", "i-mer-chen-si"),
    Sub(r"\bevacuation\b", "i-bak-yu-ey-syon"),
    Sub(r"\bevacuate\b", "i-bak-yu-eyt"),
    Sub(r"\bfirst[\s\-]aid\b", "pirst eyd"),
    Sub(r"\bflashlight\b", "plash-layt"),
    Sub(r"\bbatter(?:y|ies)\b", "ba-te-ris"),
    Sub(r"\bcharger\b", "tsar-ger"),
    Sub(r"\bportable\b", "por-ta-bol"),
    Sub(r"\bdisaster\b", "di-sas-ter"),
    Sub(r"\bresidents?\b", "re-si-dent"),
    Sub(r"\bauthorit(?:y|ies)\b", "aw-to-ri-ti"),
    Sub(r"\bresponsib(?:le|ility)\b", "ris-pon-si-bol"),
    Sub(r"\bofficial\b", "o-pi-syal"),

    # Philippine regions / place names ------------------------------------
    Sub(r"\bLuzon\b", "lu-son"),
    Sub(r"\bVisayas\b", "bi-sa-yas"),
    Sub(r"\bMindanao\b", "min-da-naw"),
    Sub(r"\bPhilippines?\b", "pi-li-pi-nas"),
    Sub(r"\bPhilippine\b", "pi-li-pin"),
    Sub(r"\bArea\s+of\s+Responsibility\b", "i-yer ov ris-pon-si-bi-li-ti"),

    # LGU / government acronyms -------------------------------------------
    Sub(r"\bLGU\b", "el-dyi-yu"),
]

# ---------------------------------------------------------------------------
# Language-specific overrides
# ---------------------------------------------------------------------------

# Tagalog: "kilometers per hour" → "ki-lo-me-tro bawat oras"
_TL_OVERRIDES: list[Sub] = [
    Sub(r"\bkilometers?\s+per\s+hour\b", "ki-lo-me-tro ba-wat o-ras"),
    Sub(r"\bkm/h\b", "ki-lo-me-tro ba-wat o-ras"),
    Sub(r"\bkph\b", "ki-lo-me-tro ba-wat o-ras"),
    Sub(r"\bkilometers?\b", "ki-lo-me-tro"),
]

# Cebuano: slightly different phrasing for speed
_CEB_OVERRIDES: list[Sub] = [
    Sub(r"\bkilometers?\s+per\s+hour\b", "ki-lo-me-tros sa usa ka oras"),
    Sub(r"\bkm/h\b", "ki-lo-me-tros sa usa ka oras"),
    Sub(r"\bkph\b", "ki-lo-me-tros sa usa ka oras"),
    Sub(r"\bkilometers?\b", "ki-lo-me-tros"),
]

# Merged tables: language-specific overrides first so they win over _COMMON
_SUBS: dict[str, list[Sub]] = {
    "tl": _TL_OVERRIDES + _COMMON,
    "ceb": _CEB_OVERRIDES + _COMMON,
}


def apply_phonetics(text: str, language: str) -> str:
    """Replace English words in *text* with phonetic equivalents for *language*.

    Only applies to "tl" and "ceb".  Returns *text* unchanged for "en" or any
    unknown language.

    Args:
        text:     Plain text output from the LLM TTS prompt.
        language: ISO language code ("tl", "ceb", or "en").

    Returns:
        Text with English vocabulary replaced by phonetic equivalents.
    """
    subs = _SUBS.get(language)
    if not subs:
        return text

    for sub in subs:
        text = re.sub(sub.pattern, sub.replacement, text, flags=re.IGNORECASE)

    return text
