# English-First Radio Script Generation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate the English radio script first, then adapt it into Tagalog and Cebuano — instead of generating all three independently from raw bulletin data.

**Architecture:** `run_step2()` in `scripts.py` branches on `language`: EN calls `_generate_radio_script` as before; TL/CEB call a new `_translate_radio_script()` that takes the English script as input. `run_batch.py` calls EN synchronously first, then TL+CEB in parallel via `starmap` to prevent a race condition writing `radio_en.md`.

**Tech Stack:** Python 3.12, pytest, Modal, Ollama (`gemma4:e4b`)

---

## File Map

| File | Change |
|---|---|
| `tests/test_core_scripts.py` | Add 3 new tests for EN-first dispatch |
| `modal_etl/core/scripts.py` | Add `_TRANSLATE_PROMPTS` dict + `_translate_radio_script()` function; update `run_step2()` branch |
| `modal_etl/run_batch.py` | Replace single `starmap` with two-phase EN-first dispatch |

---

### Task 1: Write 3 failing tests

**Files:**
- Modify: `tests/test_core_scripts.py`

- [ ] **Step 1: Add the 3 new tests**

Append to `tests/test_core_scripts.py` (after `test_clean_ocr_preserves_inline_brackets`):

```python
def test_run_step2_tl_generates_en_first_if_missing(tmp_path, monkeypatch):
    """When radio_en.md is absent and language=tl, EN is generated first then TL is translated."""
    stem = "PAGASA_TEST"
    stem_dir = tmp_path / stem
    stem_dir.mkdir()
    (stem_dir / "ocr.md").write_text("Bulletin text.", encoding="utf-8")

    gen_calls: list[tuple] = []
    trans_calls: list[tuple] = []

    def fake_generate(ocr_md, language, ollama_url, model, metadata=None):
        gen_calls.append((ocr_md, language))
        return "English script"

    def fake_translate(english_md, language, ollama_url, model):
        trans_calls.append((english_md, language))
        return "Tagalog script"

    monkeypatch.setattr("modal_etl.core.scripts._generate_radio_script", fake_generate)
    monkeypatch.setattr("modal_etl.core.scripts._translate_radio_script", fake_translate)
    monkeypatch.setattr("modal_etl.core.scripts._generate_tts_text", lambda *a, **kw: "tts")
    monkeypatch.setattr("modal_etl.core.scripts._cleanup_english_words", lambda t, *a, **kw: t)
    monkeypatch.setattr("modal_etl.core.scripts._cleanup_numbers", lambda t, *a, **kw: t)

    result = run_step2(stem, "tl", tmp_path)

    assert len(gen_calls) == 1
    assert gen_calls[0][1] == "en"
    assert (stem_dir / "radio_en.md").read_text(encoding="utf-8") == "English script"
    assert len(trans_calls) == 1
    assert trans_calls[0] == ("English script", "tl")
    assert result == stem_dir / "radio_tl.md"


def test_run_step2_tl_uses_english_when_en_exists(tmp_path, monkeypatch):
    """When radio_en.md already exists, _translate_radio_script is called directly without generating EN."""
    stem = "PAGASA_TEST"
    stem_dir = tmp_path / stem
    stem_dir.mkdir()
    (stem_dir / "ocr.md").write_text("Bulletin text.", encoding="utf-8")
    (stem_dir / "radio_en.md").write_text("Pre-existing English script", encoding="utf-8")

    gen_calls: list = []
    trans_calls: list[tuple] = []

    def fake_generate(ocr_md, language, ollama_url, model, metadata=None):
        gen_calls.append(language)
        return "Regenerated English"

    def fake_translate(english_md, language, ollama_url, model):
        trans_calls.append((english_md, language))
        return "Tagalog from existing EN"

    monkeypatch.setattr("modal_etl.core.scripts._generate_radio_script", fake_generate)
    monkeypatch.setattr("modal_etl.core.scripts._translate_radio_script", fake_translate)
    monkeypatch.setattr("modal_etl.core.scripts._generate_tts_text", lambda *a, **kw: "tts")
    monkeypatch.setattr("modal_etl.core.scripts._cleanup_english_words", lambda t, *a, **kw: t)
    monkeypatch.setattr("modal_etl.core.scripts._cleanup_numbers", lambda t, *a, **kw: t)

    run_step2(stem, "tl", tmp_path)

    assert gen_calls == [], "Should NOT call _generate_radio_script when radio_en.md exists"
    assert len(trans_calls) == 1
    assert trans_calls[0] == ("Pre-existing English script", "tl")


def test_run_step2_en_path_unchanged(tmp_path, monkeypatch):
    """For language=en, _generate_radio_script is called and _translate_radio_script is never called."""
    stem = "PAGASA_TEST"
    stem_dir = tmp_path / stem
    stem_dir.mkdir()
    (stem_dir / "ocr.md").write_text("Bulletin text.", encoding="utf-8")

    gen_calls: list = []
    trans_calls: list = []

    def fake_generate(ocr_md, language, ollama_url, model, metadata=None):
        gen_calls.append(language)
        return "English script"

    def fake_translate(english_md, language, ollama_url, model):
        trans_calls.append(language)
        return "Should not be called"

    monkeypatch.setattr("modal_etl.core.scripts._generate_radio_script", fake_generate)
    monkeypatch.setattr("modal_etl.core.scripts._translate_radio_script", fake_translate)
    monkeypatch.setattr("modal_etl.core.scripts._generate_tts_text", lambda *a, **kw: "tts")
    monkeypatch.setattr("modal_etl.core.scripts._cleanup_english_words", lambda t, *a, **kw: t)
    monkeypatch.setattr("modal_etl.core.scripts._cleanup_numbers", lambda t, *a, **kw: t)

    run_step2(stem, "en", tmp_path)

    assert gen_calls == ["en"]
    assert trans_calls == [], "_translate_radio_script must not be called for language=en"
```

- [ ] **Step 2: Run the tests to confirm they fail**

```bash
uv run pytest tests/test_core_scripts.py::test_run_step2_tl_generates_en_first_if_missing tests/test_core_scripts.py::test_run_step2_tl_uses_english_when_en_exists tests/test_core_scripts.py::test_run_step2_en_path_unchanged -v
```

Expected: 3 failures — `AttributeError: module 'modal_etl.core.scripts' has no attribute '_translate_radio_script'`

- [ ] **Step 3: Commit the failing tests**

```bash
git add tests/test_core_scripts.py
git commit -m "test: add failing tests for EN-first radio script dispatch"
```

---

### Task 2: Add `_TRANSLATE_PROMPTS` and `_translate_radio_script()`

**Files:**
- Modify: `modal_etl/core/scripts.py`

- [ ] **Step 1: Add `_TRANSLATE_PROMPTS` after `_RADIO_PROMPTS`**

Insert after line 120 (`}` closing `_RADIO_PROMPTS`), before the `# TTS plain text prompts` section divider:

```python
# ---------------------------------------------------------------------------
# Translation prompts — adapt English script into TL/CEB
# ---------------------------------------------------------------------------

_TRANSLATE_PROMPTS: dict[str, dict[str, str]] = {
    "tl": {
        "system": _RADIO_PROMPTS["tl"]["system"],
        "user": (
            "Narito ang kumpletong pahayag sa Ingles tungkol sa bagyo. I-adapt ito sa natural na Tagalog.\n\n"
            "{english_script}\n\n"
            "MAHALAGA: Panatilihin ang LAHAT ng impormasyon mula sa Ingles — pangalan ng bagyo, "
            "lokasyon, landas, bawat apektadong lugar na may Signal level, kung ano ang dapat gawin, "
            "at oras ng susunod na update. Walang detalye ang maaaring maiwanan.\n\n"
            "Isulat ang pahayag sa Tagalog ngayon. Hindi hihigit sa 200 salita. "
            "Puro Tagalog. Walang headings, walang markdown."
        ),
    },
    "ceb": {
        "system": _RADIO_PROMPTS["ceb"]["system"],
        "user": (
            "Ania ang kompletong pahimangno sa Ingles bahin sa bagyo. I-adapt kini ngadto sa natural nga Cebuano.\n\n"
            "{english_script}\n\n"
            "IMPORTANTE: Panatilihon ang TANAN nga impormasyon gikan sa Ingles — ngalan sa bagyo, "
            "lokasyon, dalan, matag apektadong lugar nga adunay Signal level, unsa ang buhaton, "
            "ug oras sa sunod nga update. Walay detalye ang maaaring mawala.\n\n"
            "Isulat ang pahimangno sa Cebuano karon. Dili molapas sa 200 ka pulong. "
            "Puro Cebuano. Walay headings, walay markdown."
        ),
    },
}
```

- [ ] **Step 2: Add `_translate_radio_script()` after `_generate_radio_script()`**

Insert after the closing of `_generate_radio_script()` (after line 554, before `_generate_tts_text`):

```python
def _translate_radio_script(english_md: str, language: str, ollama_url: str, model: str) -> str:
    p = _TRANSLATE_PROMPTS[language]
    return call_ollama_chat(
        url=ollama_url,
        model=model,
        system=p["system"],
        user=p["user"].format(english_script=english_md),
    )
```

- [ ] **Step 3: Run the 3 new tests to confirm they still fail (dispatch logic not updated yet)**

```bash
uv run pytest tests/test_core_scripts.py::test_run_step2_tl_generates_en_first_if_missing tests/test_core_scripts.py::test_run_step2_tl_uses_english_when_en_exists tests/test_core_scripts.py::test_run_step2_en_path_unchanged -v
```

Expected: still failing — monkeypatch for `_translate_radio_script` now resolves, but dispatch not wired yet.

- [ ] **Step 4: Commit**

```bash
git add modal_etl/core/scripts.py
git commit -m "feat: add _TRANSLATE_PROMPTS and _translate_radio_script() to scripts.py"
```

---

### Task 3: Update `run_step2()` dispatch logic

**Files:**
- Modify: `modal_etl/core/scripts.py` (lines 636–637)

- [ ] **Step 1: Replace the radio script generation line in `run_step2()`**

Current code (line 636–637 in `run_step2()`):

```python
    radio_md = _generate_radio_script(ocr_md, language, ollama_url, model, metadata=metadata)
    radio_path.write_text(radio_md, encoding="utf-8")
```

Replace with:

```python
    if language == "en":
        radio_md = _generate_radio_script(ocr_md, "en", ollama_url, model, metadata=metadata)
    else:
        en_radio_path = out_dir / "radio_en.md"
        if not en_radio_path.exists():
            en_radio_md = _generate_radio_script(ocr_md, "en", ollama_url, model, metadata=metadata)
            en_radio_path.write_text(en_radio_md, encoding="utf-8")
            print(f"[run_step2] {stem}/{language}: auto-generated radio_en.md")
        english_md = en_radio_path.read_text(encoding="utf-8")
        radio_md = _translate_radio_script(english_md, language, ollama_url, model)
    radio_path.write_text(radio_md, encoding="utf-8")
```

The rest of `run_step2()` (tts_text, cleanup, tts_path) is unchanged.

- [ ] **Step 2: Run the 3 new tests — they should now pass**

```bash
uv run pytest tests/test_core_scripts.py::test_run_step2_tl_generates_en_first_if_missing tests/test_core_scripts.py::test_run_step2_tl_uses_english_when_en_exists tests/test_core_scripts.py::test_run_step2_en_path_unchanged -v
```

Expected: all 3 PASS.

- [ ] **Step 3: Run the full existing test suite to verify no regressions**

```bash
uv run pytest tests/test_core_scripts.py -v
```

Expected: all 8 tests PASS (5 existing + 3 new).

- [ ] **Step 4: Commit**

```bash
git add modal_etl/core/scripts.py
git commit -m "feat: update run_step2() — EN-first dispatch, TL/CEB translate from radio_en.md"
```

---

### Task 4: Update `run_batch.py` EN-first ordering

**Files:**
- Modify: `modal_etl/run_batch.py` (lines 288–298)

- [ ] **Step 1: Replace the Step 2 `starmap` block**

Current code (around line 289–298):

```python
        # Step 2
        if step in (0, 2):
            print("  Step 2: Radio scripts + TTS text (3 languages in parallel)...")
            t0 = time.time()
            try:
                list(step2_scripts.starmap([(stem, lang, force) for lang in LANGUAGES]))
```

Replace with:

```python
        # Step 2
        if step in (0, 2):
            print("  Step 2: Radio scripts + TTS text (EN first, then TL+CEB in parallel)...")
            t0 = time.time()
            try:
                # Phase 1: English first — TL/CEB containers read radio_en.md rather than racing to create it
                step2_scripts.remote(stem, "en", force)
                # Phase 2: Tagalog and Cebuano translate from radio_en.md in parallel
                list(step2_scripts.starmap([(stem, lang, force) for lang in LANGUAGES if lang != "en"]))
```

Everything after `list(step2_scripts.starmap(...))` (the `bulletin_result` assignment, `except` block, etc.) is unchanged.

- [ ] **Step 2: Verify the file looks correct**

```bash
uv run python -c "import ast, pathlib; ast.parse(pathlib.Path('modal_etl/run_batch.py').read_text()); print('syntax ok')"
```

Expected: `syntax ok`

- [ ] **Step 3: Commit**

```bash
git add modal_etl/run_batch.py
git commit -m "feat: run_batch.py — EN-first then TL+CEB parallel to prevent radio_en.md race"
```

---

### Task 5: Full test suite + verify imports

**Files:**
- No changes

- [ ] **Step 1: Run the complete test suite**

```bash
uv run pytest tests/ -v
```

Expected: all tests PASS. Note the 3 new tests in `test_core_scripts.py`.

- [ ] **Step 2: Verify scripts.py imports cleanly**

```bash
uv run python -c "from modal_etl.core.scripts import run_step2, _translate_radio_script, _TRANSLATE_PROMPTS; print('imports ok')"
```

Expected: `imports ok`

- [ ] **Step 3: Spot-check `_TRANSLATE_PROMPTS` references correct system prompts**

```bash
uv run python -c "
from modal_etl.core.scripts import _TRANSLATE_PROMPTS, _RADIO_PROMPTS
assert _TRANSLATE_PROMPTS['tl']['system'] is _RADIO_PROMPTS['tl']['system'], 'TL system prompt must be the same object'
assert _TRANSLATE_PROMPTS['ceb']['system'] is _RADIO_PROMPTS['ceb']['system'], 'CEB system prompt must be the same object'
print('system prompt identity ok')
"
```

Expected: `system prompt identity ok`
