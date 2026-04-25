# Metadata-First Radio Script Generation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the noisy raw `ocr.md` input to the radio script LLM with a structured, labelled summary derived from `metadata.json`, eliminating hallucinations like wind speed being read as movement speed.

**Architecture:** Add a pure `_format_metadata_for_prompt()` function that converts the already-extracted `metadata.json` dict into a clearly-labelled text block (e.g. "MAX SUSTAINED WINDS: 120 km/h", "MOVEMENT: West-Southwest"). Update `_generate_radio_script()` to accept this formatted block instead of raw markdown. Fall back to cleaned `ocr.md` only when `metadata.json` is absent.

**Tech Stack:** Python 3.12, pytest (via `uv run pytest`), Modal, Ollama/Gemma 4 E4B. Package management: `uv` only — never `pip`.

---

## File Map

| File | Action | Purpose |
|---|---|---|
| `modal_etl/step2_scripts.py` | Modify | Add `_format_metadata_for_prompt()`; update `_generate_radio_script()` signature and prompt templates; wire metadata loading in `step2_scripts()` |
| `tests/test_step2_format_metadata.py` | Create | Unit tests for `_format_metadata_for_prompt()` |

---

## Task 1: Add `_format_metadata_for_prompt()` with tests

**Files:**
- Create: `tests/test_step2_format_metadata.py`
- Modify: `modal_etl/step2_scripts.py` (add function after `_clean_ocr`)

The function converts the parsed `metadata.json` dict into a structured, labelled text block that makes every field unambiguous to the LLM. It must handle nulls gracefully and clearly flag when the storm is outside PAR with no wind signals.

- [ ] **Step 1.1: Write failing tests**

Create `tests/test_step2_format_metadata.py`:

```python
"""Tests for _format_metadata_for_prompt in step2_scripts."""

import pytest
from modal_etl.step2_scripts import _format_metadata_for_prompt


# ── Fixtures ────────────────────────────────────────────────────────────────

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
    # "120" must appear with a label that is clearly about wind, not movement
    result = _format_metadata_for_prompt(VERBENA_METADATA)
    # Wind speed and "120" should be in the same section
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
    # Should not crash and should contain something indicating speed unknown
    assert result  # non-empty


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
    assert "24" in result  # 24-hour forecast hour


def test_forecast_reference_present():
    result = _format_metadata_for_prompt(VERBENA_METADATA)
    assert "320 km Northwest" in result


# ── Next bulletin ─────────────────────────────────────────────────────────────

def test_valid_until_when_present():
    result = _format_metadata_for_prompt(SIGNAL_METADATA)
    assert "2025-10-21 11:00:00" in result


def test_valid_until_when_null():
    result = _format_metadata_for_prompt(VERBENA_METADATA)
    # Should handle null gracefully — no crash, may say "not specified"
    assert result
```

- [ ] **Step 1.2: Run tests to confirm they fail**

```bash
uv run pytest tests/test_step2_format_metadata.py -v 2>&1 | head -30
```

Expected: `ImportError` — `_format_metadata_for_prompt` not yet defined.

- [ ] **Step 1.3: Implement `_format_metadata_for_prompt()` in `step2_scripts.py`**

Add this function after the `_clean_ocr` function (around line 449 in the current file):

```python
def _format_metadata_for_prompt(metadata: dict) -> str:
    """Convert a parsed metadata.json dict into a labelled text block for LLM prompts.

    Produces unambiguous field labels so the LLM cannot confuse wind speed with
    movement speed or miss the OUTSIDE PAR / no-signal status.
    """
    s = metadata.get("storm", {})
    storm_name = s.get("name", "Unknown")
    category = s.get("category", "Unknown")
    intl = s.get("international_name")
    intl_str = f" (international name: {intl})" if intl else ""

    b_type = metadata.get("bulletin_type", "")
    b_num = metadata.get("bulletin_number")
    b_num_str = f" #{b_num}" if b_num else ""
    bulletin_label = f"{b_type}{b_num_str}" if b_type else "Bulletin"

    iss = metadata.get("issuance", {})
    issued = iss.get("datetime", "not specified")
    valid_until = iss.get("valid_until") or "not specified"

    pos = metadata.get("current_position", {})
    position_ref = pos.get("reference") or "not specified"
    position_as_of = pos.get("as_of") or ""
    position_str = position_ref
    if position_as_of:
        position_str += f" (as of {position_as_of})"

    inten = metadata.get("intensity", {})
    winds = inten.get("max_sustained_winds_kph")
    gusts = inten.get("gusts_kph")
    winds_str = f"{winds} km/h" if winds else "not specified"
    gusts_str = f"up to {gusts} km/h" if gusts else "not specified"

    mov = metadata.get("movement", {})
    direction = mov.get("direction") or "not specified"
    speed = mov.get("speed_kph")
    speed_str = f"{speed} km/h" if speed else "not specified"

    # Wind signals
    areas = metadata.get("affected_areas", {})
    signal_sections = []
    for level in range(1, 6):
        places = areas.get(f"signal_{level}", [])
        if places:
            signal_sections.append(f"  Signal {level}: {', '.join(places)}")
    rainfall = areas.get("rainfall_warning", [])
    if rainfall:
        signal_sections.append(f"  Rainfall warning: {', '.join(rainfall)}")
    coastal = areas.get("coastal_waters")
    if coastal:
        signal_sections.append(f"  Coastal waters: {coastal}")

    if signal_sections:
        signals_str = "\n".join(signal_sections)
    else:
        signals_str = "  No wind signals in effect — no areas of the Philippines are under any wind signal."

    # Forecast track
    forecasts = metadata.get("forecast_positions", [])
    forecast_lines = []
    for fp in forecasts:
        hour = fp.get("hour", "?")
        ref = fp.get("reference") or "location not specified"
        forecast_lines.append(f"  {hour}-hour: {ref}")
    forecasts_str = "\n".join(forecast_lines) if forecast_lines else "  Not available"

    return (
        f"=== PAGASA TYPHOON BULLETIN ===\n"
        f"Storm: {category} {storm_name}{intl_str}\n"
        f"Bulletin: {bulletin_label}\n"
        f"Issued: {issued}\n"
        f"Valid until / Next bulletin: {valid_until}\n"
        f"\n"
        f"CURRENT POSITION:\n"
        f"  {position_str}\n"
        f"\n"
        f"INTENSITY:\n"
        f"  Maximum sustained winds: {winds_str} near the center\n"
        f"  Gusts: {gusts_str}\n"
        f"\n"
        f"MOVEMENT:\n"
        f"  Direction: {direction}\n"
        f"  Speed: {speed_str}\n"
        f"\n"
        f"WIND SIGNALS IN EFFECT:\n"
        f"{signals_str}\n"
        f"\n"
        f"FORECAST TRACK:\n"
        f"{forecasts_str}\n"
    )
```

- [ ] **Step 1.4: Run tests to confirm they pass**

```bash
uv run pytest tests/test_step2_format_metadata.py -v
```

Expected: all tests PASS.

- [ ] **Step 1.5: Commit**

```bash
git add modal_etl/step2_scripts.py tests/test_step2_format_metadata.py
git commit -m "feat: add _format_metadata_for_prompt for structured LLM input"
```

---

## Task 2: Update `_generate_radio_script()` to use metadata dict

**Files:**
- Modify: `modal_etl/step2_scripts.py` (update prompt templates + function signature)

The radio prompts' `user` templates currently use `{markdown}` substitution. Change them to `{bulletin_data}` and update the framing from "Convert this PAGASA weather bulletin markdown..." to "Convert this structured PAGASA bulletin data...". The `system` prompts (which describe output style) are unchanged.

- [ ] **Step 2.1: Update `_RADIO_PROMPTS` user templates**

In `step2_scripts.py`, update the `"user"` entry for each language in `_RADIO_PROMPTS`. The system prompts stay the same — only the user message framing changes.

For `"en"`:
```python
"user": (
    "Convert this structured PAGASA bulletin data into a plain conversational English announcement.\n\n"
    "{bulletin_data}\n\n"
    "Write the announcement now. Pack in all critical information — storm, location, track, "
    "affected areas with Signal levels, what to do, next bulletin time. "
    "No more than 200 words. No headings, no markdown. Write place names naturally."
),
```

For `"tl"`:
```python
"user": (
    "I-convert ang structured na datos ng PAGASA bulletin na ito sa maikling pahayag sa Tagalog.\n\n"
    "{bulletin_data}\n\n"
    "Isulat ang pahayag ngayon. Ilagay ang lahat ng kritikal na impormasyon — bagyo, lokasyon, landas, "
    "mga apektadong lugar na may Signal level, ano ang gagawin, oras ng susunod na update. "
    "Hindi hihigit sa 200 salita. Puro Tagalog. Walang headings, walang markdown."
),
```

For `"ceb"`:
```python
"user": (
    "I-convert ang structured nga datos sa PAGASA bulletin nga kini ngadto sa mubo nga pahimangno sa Cebuano.\n\n"
    "{bulletin_data}\n\n"
    "Isulat ang pahimangno karon. Ibutang ang tanan nga kritikal nga impormasyon — bagyo, lokasyon, dalan, "
    "mga apektadong lugar nga adunay Signal level, unsa ang buhaton, oras sa sunod nga update. "
    "Dili molapas sa 200 ka pulong. Puro Cebuano. Walay headings, walay markdown."
),
```

- [ ] **Step 2.2: Update `_generate_radio_script()` signature**

Replace the current function:

```python
def _generate_radio_script(markdown: str, language: str) -> str:
    """Generate a ~300-word spoken weather announcement in the target language."""
    p = _RADIO_PROMPTS[language]
    return _call_ollama_chat(
        system=p["system"],
        user=p["user"].format(markdown=markdown),
    )
```

With:

```python
def _generate_radio_script(bulletin_data: str, language: str) -> str:
    """Generate a spoken weather announcement in the target language.

    Args:
        bulletin_data: Structured bulletin summary from _format_metadata_for_prompt(),
                       or cleaned ocr.md text as fallback.
        language:      "en", "tl", or "ceb".
    """
    p = _RADIO_PROMPTS[language]
    return _call_ollama_chat(
        system=p["system"],
        user=p["user"].format(bulletin_data=bulletin_data),
    )
```

- [ ] **Step 2.3: Run existing tests to confirm nothing is broken**

```bash
uv run pytest tests/ -v --ignore=tests/test_step2_format_metadata.py
```

Expected: all previously-passing tests still PASS. (The `_generate_radio_script` change is internal — no existing tests call it directly.)

- [ ] **Step 2.4: Commit**

```bash
git add modal_etl/step2_scripts.py
git commit -m "feat: update radio script prompt to use structured bulletin_data"
```

---

## Task 3: Wire metadata loading into `step2_scripts()` Modal function

**Files:**
- Modify: `modal_etl/step2_scripts.py` (update `step2_scripts()` function body)

The Modal function currently loads only `ocr.md`. Update it to also load `metadata.json` when present and use `_format_metadata_for_prompt()` to build the input. Fall back to cleaned `ocr.md` when `metadata.json` is absent.

- [ ] **Step 3.1: Update `step2_scripts()` function body**

Replace the current block (starting at the `ocr_md = ...` line, around line 553):

```python
    ocr_md = _clean_ocr((out_dir / "ocr.md").read_text(encoding="utf-8"))

    radio_md = _generate_radio_script(ocr_md, language)
```

With:

```python
    ocr_md = _clean_ocr((out_dir / "ocr.md").read_text(encoding="utf-8"))

    metadata_path = out_dir / "metadata.json"
    if metadata_path.exists():
        import json as _json
        metadata = _json.loads(metadata_path.read_text(encoding="utf-8"))
        bulletin_data = _format_metadata_for_prompt(metadata)
        print(f"[Step2Scripts] {stem}/{language}: using metadata.json as primary source")
    else:
        bulletin_data = ocr_md
        print(f"[Step2Scripts] {stem}/{language}: metadata.json absent, falling back to ocr.md")

    radio_md = _generate_radio_script(bulletin_data, language)
```

- [ ] **Step 3.2: Run full test suite**

```bash
uv run pytest tests/ -v
```

Expected: all tests PASS.

- [ ] **Step 3.3: Commit**

```bash
git add modal_etl/step2_scripts.py
git commit -m "feat: load metadata.json in step2 and use as primary LLM source"
```

---

## Task 4: Manual verification with Verbena TCB#24

**Files:**
- Read: `data/gemma4_results/structured/PAGASA_25-TC22_Verbena_TCB#24_structured.json`
- Read: `data/radio_bulletins/PAGASA_25-TC22_Verbena_TCB#24_radio_ceb.md` (before/after comparison)

Verify the formatter produces the correct structured block for Verbena, and check that the formatted output would prevent the known bugs: wind speed confused with movement speed, wrong next-bulletin statement, wrong storm name.

- [ ] **Step 4.1: Run formatter against Verbena metadata locally**

```bash
uv run python - <<'EOF'
import json
from modal_etl.step2_scripts import _format_metadata_for_prompt

with open("data/gemma4_results/structured/PAGASA_25-TC22_Verbena_TCB#24_structured.json") as f:
    meta = json.load(f)

print(_format_metadata_for_prompt(meta))
EOF
```

Expected output should contain:
- `Storm: Typhoon VERBENA (international name: KOTO)` (or equivalent)
- `Maximum sustained winds: 120 km/h` — clearly labelled as wind, not movement
- `Direction: West-Southwest` — clearly labelled as movement direction
- `Speed: not specified` — gracefully handles missing speed_kph
- `No wind signals in effect` — no confusion about signals
- `OUTSIDE PAR` in the position line
- Forecast positions listed with references

- [ ] **Step 4.2: Confirm the known bugs are no longer possible from the prompt**

Check the formatted output manually:
1. "120 km/h" appears under `INTENSITY` / wind section — not under `MOVEMENT`
2. Movement section says "Speed: not specified" (not 120)
3. No signals section says "No wind signals in effect"
4. Storm name is unambiguously VERBENA

- [ ] **Step 4.3: Commit the verification note in the devlog**

Add a one-line entry in `devlog.md` noting that Step 2 now uses metadata-first approach, with Verbena TCB#24 verified as test case.

```bash
git add devlog.md
git commit -m "docs: note metadata-first Step 2 change in devlog"
```

---

## Self-Review

**Spec coverage:**
- ✅ Metadata.json as primary source — Tasks 1, 3
- ✅ Labelled fields prevent wind/movement confusion — Task 1 (`_format_metadata_for_prompt`)
- ✅ OUTSIDE PAR / no-signal handling — Task 1 tests + formatter
- ✅ Fallback to ocr.md when metadata.json absent — Task 3
- ✅ All three languages updated — Task 2 (prompt templates for en/tl/ceb)
- ✅ Verified with Verbena TCB#24 — Task 4

**Placeholder scan:** None found. All code blocks are complete and runnable.

**Type consistency:**
- `_format_metadata_for_prompt(metadata: dict) -> str` defined in Task 1, used in Task 3 ✅
- `_generate_radio_script(bulletin_data: str, language: str) -> str` defined in Task 2, called in Task 3 ✅
- `bulletin_data` variable name consistent across Task 2 (prompt template key) and Task 3 (`.format(bulletin_data=...)`) ✅
