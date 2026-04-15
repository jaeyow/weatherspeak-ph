# TTS Pipeline — Dialect-Pure Text Generation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the markdown-strip TTS pipeline with a two-flow approach: notebook 06 generates dialect-pure Cebuano plain text via a second Gemma4 prompt, and notebook 08 uses sentence-level synthesis with 500ms/750ms silence stitching.

**Architecture:** Notebook 06 produces both a markdown radio script (for display) and a `_tts_ceb.txt` plain text file (for audio). Notebook 08 reads the `.txt` directly, splits it into sentences via `prepare_mms_sentences`, and synthesizes each sentence separately, stitching with silence pauses. No markdown stripping step.

**Tech Stack:** Python 3.12, `re` (stdlib), `pydub.AudioSegment`, `torch`, `transformers.VitsModel`, `AutoTokenizer`, `pytest`, `uv`

---

## File Map

| File | Action | Purpose |
|---|---|---|
| `tests/test_mms_synthesis.py` | Modify | Add `prepare_mms_sentences` + 7 tests; update `synthesize_with_mms` to new signature + update 4 existing tests + add 2 pause tests |
| `notebooks/06-radio-bulletin.ipynb` | Modify | Insert 3 cells after cell `b8c9d0e1`: markdown heading, `TTS_PROMPTS` dict, `generate_tts_text()` run |
| `notebooks/08-mms-tts-experiment.ipynb` | Modify | Update setup cell (cell `7abe84e4`), replace preprocessing cell (cell `38715dd2`), update synthesis cell (cell `a295e144`) |

---

### Task 1: `prepare_mms_sentences` — TDD

**Files:**
- Modify: `tests/test_mms_synthesis.py`

- [ ] **Step 1: Add `import re` and stub + 7 failing tests to end of file**

Add `import re` to the imports block at the top of the file (after `from pydub import AudioSegment`).

Append the stub and tests to the end of `tests/test_mms_synthesis.py`:

```python
def prepare_mms_sentences(text: str) -> list[tuple[str, bool]]:
    pass  # stub — tests must fail


def test_prepare_mms_sentences_single_sentence():
    result = prepare_mms_sentences("Hello world.")
    assert result == [("hello world", True)]


def test_prepare_mms_sentences_multi_sentence_paragraph():
    result = prepare_mms_sentences("Maayong buntag. Pag-andam na mo.")
    assert len(result) == 2
    assert result[0] == ("maayong buntag", False)
    assert result[1] == ("pag-andam na mo", True)


def test_prepare_mms_sentences_two_paragraphs():
    result = prepare_mms_sentences("First sentence.\n\nSecond sentence.")
    assert len(result) == 2
    assert result[0] == ("first sentence", True)
    assert result[1] == ("second sentence", True)


def test_prepare_mms_sentences_em_dash():
    result = prepare_mms_sentences("Ang bagyo\u2014mabilis mokaon.")
    assert len(result) == 1
    assert "\u2014" not in result[0][0]
    assert "bagyo" in result[0][0]
    assert "mabilis" in result[0][0]


def test_prepare_mms_sentences_apostrophe_in_word():
    result = prepare_mms_sentences("Mo'y dako kaayo.")
    assert len(result) == 1
    assert result[0][0] == "mo'y dako kaayo"


def test_prepare_mms_sentences_standalone_quotes_stripped():
    result = prepare_mms_sentences("'Hello world'.")
    assert len(result) == 1
    assert "'" not in result[0][0]
    assert result[0][0] == "hello world"


def test_prepare_mms_sentences_lowercase_and_no_punctuation():
    result = prepare_mms_sentences("PAGASA Signal Number TWO warns!")
    assert len(result) == 1
    assert result[0][0] == "pagasa signal number two warns"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/josereyes/Dev/gemma4-hackathon && uv run pytest tests/test_mms_synthesis.py -k "prepare_mms_sentences" -v
```

Expected: 7 FAILED (stub returns `None`, not a list)

- [ ] **Step 3: Replace stub with real implementation**

Replace the `pass` body of `prepare_mms_sentences` with:

```python
def prepare_mms_sentences(text: str) -> list[tuple[str, bool]]:
    """Split plain text into MMS-ready sentences with paragraph boundary flags.

    Returns list of (sentence, is_paragraph_end) tuples where:
    - sentence: lowercase, punctuation-stripped (in-word apostrophes/hyphens preserved)
    - is_paragraph_end: True if last sentence of its paragraph
    """
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    result = []
    for paragraph in paragraphs:
        sentences = re.split(r'(?<=[.!?])\s+', paragraph)
        sentences = [s.strip() for s in sentences if s.strip()]
        for sent_idx, sentence in enumerate(sentences):
            is_last_in_para = (sent_idx == len(sentences) - 1)
            sentence = sentence.lower()
            # Remove all punctuation except apostrophes and hyphens
            s = re.sub(r"[^\w\s'\-]", " ", sentence)
            # Remove apostrophes/hyphens not flanked by word characters (standalone)
            s = re.sub(r"(?<!\w)['\-]|['\-](?!\w)", " ", s)
            sentence = re.sub(r"\s+", " ", s).strip()
            if sentence:
                result.append((sentence, is_last_in_para))
    return result
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /Users/josereyes/Dev/gemma4-hackathon && uv run pytest tests/test_mms_synthesis.py -k "prepare_mms_sentences" -v
```

Expected: 7 PASSED

- [ ] **Step 5: Commit**

```bash
cd /Users/josereyes/Dev/gemma4-hackathon && git add tests/test_mms_synthesis.py && git commit -m "feat: add prepare_mms_sentences with TDD tests"
```

---

### Task 2: Update `synthesize_with_mms` — sentence-level synthesis

**Files:**
- Modify: `tests/test_mms_synthesis.py`

- [ ] **Step 1: Add 2 new failing tests for pause behavior**

Append to end of `tests/test_mms_synthesis.py`:

```python
def test_synthesize_paragraph_pause_longer_than_sentence_pause(tmp_path):
    """MP3 with paragraph pause (750ms) is longer than with sentence pause (500ms)."""
    sentence_path = tmp_path / "sentence.mp3"
    paragraph_path = tmp_path / "paragraph.mp3"
    mock_model = _make_mock_model(num_samples=8000)
    mock_tok = _make_mock_tokenizer()
    synthesize_with_mms(
        [("hello world", False)],
        mock_model,
        mock_tok,
        sentence_path,
        sentence_pause_ms=500,
        paragraph_pause_ms=750,
    )
    synthesize_with_mms(
        [("hello world", True)],
        mock_model,
        mock_tok,
        paragraph_path,
        sentence_pause_ms=500,
        paragraph_pause_ms=750,
    )
    sentence_dur = len(AudioSegment.from_mp3(str(sentence_path)))
    paragraph_dur = len(AudioSegment.from_mp3(str(paragraph_path)))
    assert paragraph_dur > sentence_dur


def test_synthesize_two_sentences_longer_than_one(tmp_path):
    """Two sentences produce a longer MP3 than one sentence."""
    one_path = tmp_path / "one.mp3"
    two_path = tmp_path / "two.mp3"
    mock_model = _make_mock_model(num_samples=8000)
    mock_tok = _make_mock_tokenizer()
    synthesize_with_mms(
        [("hello world", True)],
        mock_model,
        mock_tok,
        one_path,
    )
    synthesize_with_mms(
        [("hello world", False), ("goodbye world", True)],
        mock_model,
        mock_tok,
        two_path,
    )
    one_dur = len(AudioSegment.from_mp3(str(one_path)))
    two_dur = len(AudioSegment.from_mp3(str(two_path)))
    assert two_dur > one_dur
```

- [ ] **Step 2: Run new tests to verify they fail**

```bash
cd /Users/josereyes/Dev/gemma4-hackathon && uv run pytest tests/test_mms_synthesis.py -k "paragraph_pause or two_sentences" -v
```

Expected: 2 FAILED (old `synthesize_with_mms` takes `str`, not `list[tuple]`)

- [ ] **Step 3: Replace `synthesize_with_mms` and update 4 existing tests**

Replace the entire `synthesize_with_mms` function definition (currently lines 14–51) with:

```python
def synthesize_with_mms(
    sentences: list[tuple[str, bool]],
    model,
    tokenizer,
    output_path: Path,
    sample_rate: int | None = None,
    sentence_pause_ms: int = 500,
    paragraph_pause_ms: int = 750,
) -> Path:
    """Synthesize sentences to MP3 using a HuggingFace VitsModel with silence stitching.

    Args:
        sentences: List of (sentence, is_paragraph_end) from prepare_mms_sentences().
        model: Loaded VitsModel instance.
        tokenizer: Loaded AutoTokenizer instance.
        output_path: Destination MP3 path.
        sample_rate: Override model's native sample rate if needed.
        sentence_pause_ms: Silence after each non-final sentence in a paragraph (ms).
        paragraph_pause_ms: Silence after the last sentence of each paragraph (ms).

    Returns:
        output_path on success.
    """
    rate = sample_rate or model.config.sampling_rate
    combined = AudioSegment.empty()
    for sentence, is_paragraph_end in sentences:
        if not sentence.strip():
            continue
        inputs = tokenizer(sentence, return_tensors="pt")
        with torch.no_grad():
            waveform = model(**inputs).waveform
        pcm = (waveform.squeeze().numpy() * 32_767).clip(-32_768, 32_767).astype(np.int16)
        segment = AudioSegment(pcm.tobytes(), frame_rate=rate, sample_width=2, channels=1)
        combined += segment
        pause_ms = paragraph_pause_ms if is_paragraph_end else sentence_pause_ms
        combined += AudioSegment.silent(duration=pause_ms, frame_rate=rate)
    combined.export(str(output_path), format="mp3", bitrate="128k")
    return output_path
```

Update the 4 existing test functions to pass `list[tuple[str, bool]]` instead of a bare string:

```python
def test_synthesize_creates_mp3_file(tmp_path):
    output_path = tmp_path / "output.mp3"
    synthesize_with_mms(
        [("hello world", True)],
        _make_mock_model(),
        _make_mock_tokenizer(),
        output_path,
    )
    assert output_path.exists()


def test_synthesize_returns_output_path(tmp_path):
    output_path = tmp_path / "output.mp3"
    result = synthesize_with_mms(
        [("hello world", True)],
        _make_mock_model(),
        _make_mock_tokenizer(),
        output_path,
    )
    assert result == output_path


def test_synthesize_mp3_is_non_empty(tmp_path):
    output_path = tmp_path / "output.mp3"
    synthesize_with_mms(
        [("hello world", True)],
        _make_mock_model(num_samples=16_000),
        _make_mock_tokenizer(),
        output_path,
    )
    assert output_path.stat().st_size > 0


def test_synthesize_respects_sample_rate_override(tmp_path):
    """sample_rate kwarg overrides model.config.sampling_rate."""
    output_path = tmp_path / "output.mp3"
    result = synthesize_with_mms(
        [("test", True)],
        _make_mock_model(num_samples=22_050, sample_rate=16_000),
        _make_mock_tokenizer(),
        output_path,
        sample_rate=22_050,
    )
    assert result.exists()
```

- [ ] **Step 4: Run all tests to verify they pass**

```bash
cd /Users/josereyes/Dev/gemma4-hackathon && uv run pytest tests/test_mms_synthesis.py -v
```

Expected: 13 PASSED (7 prepare_mms_sentences + 4 updated existing + 2 new pause tests)

- [ ] **Step 5: Commit**

```bash
cd /Users/josereyes/Dev/gemma4-hackathon && git add tests/test_mms_synthesis.py && git commit -m "feat: update synthesize_with_mms to sentence-level synthesis with silence stitching"
```

---

### Task 3: Notebook 06 — add TTS plain text generation

**Files:**
- Modify: `notebooks/06-radio-bulletin.ipynb`

Insert 3 new cells after cell `b8c9d0e1` (the `generate_radio_bulletin` run cell at index 7). Use `NotebookEdit` with `insert_after` targeting cell `b8c9d0e1`.

- [ ] **Step 1: Insert markdown heading cell after `b8c9d0e1`**

Insert a new markdown cell immediately after cell `b8c9d0e1`:

```markdown
## 6. TTS Plain Text Generation — Cebuano

Generate a TTS-optimized plain text version of each Cebuano radio script via a second
Gemma4 prompt. This file feeds directly into notebook 08 — no markdown stripping needed.

**Output:** `data/radio_bulletins/{stem}_tts_ceb.txt`
```

- [ ] **Step 2: Insert `TTS_PROMPTS` cell after the markdown heading**

Insert a new code cell after the markdown cell from Step 1:

```python
TTS_PROMPTS = {
    "ceb": {
        "system": """Ikaw usa ka espesyalista sa Cebuano nga nagsulat og plain text nga angay para sa text-to-speech synthesis.

Ang imong trabaho:
- Basaha ang markdown radio script nga gihatag
- Isulat kini pag-usab isip natural nga flowing prose SA CEBUANO LAMANG — walay markdown
- WALA markdown: wala headings (#), wala bullet points (-), wala asterisks (*), wala bold/italic
- Para sa mga English proper nouns o teknikal nga termino, i-spell sila phonetically sa Cebuano:
  - PAGASA → pa-ga-sa
  - Northern Luzon → nor-dern lu-son
  - Signal Number One / Two / Three → sig-nal nam-ber wan / tu / tri
  - tropical depression → tro-pi-kal di-pre-syon
  - tropical storm → tro-pi-kal storm
  - kilometers per hour → ki-lo-me-tros sa usa ka oras
  - northeast / southeast / northwest / southwest → nor-ist / sow-ist / nor-west / sow-west
- Pahimusa ang paragraph structure: blank lines tali sa mga paragraph
- AYAW pagdugang og bisan unsa nga texto nga wala sa orihinal nga script
- Output: plain text lamang, walay bisan unsang markup o formatting characters""",

        "user_template": (
            "Basaha kining markdown radio script ug isulat kini pag-usab isip TTS-ready plain Cebuano text.\n\n"
            "{markdown}\n\n"
            "Isulat ang plain Cebuano text karon. Cebuano nga pulong lamang, phonetically spelled kung "
            "kinahanglan, paragraph breaks (blank lines) para sa natural nga pausing. Walay markdown."
        ),
    },
}


def build_tts_prompt(markdown_script: str, language: str) -> str:
    """Build the user prompt for TTS text generation."""
    return TTS_PROMPTS[language]["user_template"].format(markdown=markdown_script)


print("✓ TTS_PROMPTS defined for CEB")
print(f"  ceb: system={len(TTS_PROMPTS['ceb']['system'])} chars")
```

- [ ] **Step 3: Insert `generate_tts_text()` + run cell after `TTS_PROMPTS`**

Insert a new code cell after the `TTS_PROMPTS` cell:

```python
def generate_tts_text(bulletin: dict, language: str) -> dict:
    """Call Gemma 4 to generate a TTS-ready plain text script for one bulletin."""
    stem = bulletin["stem"]
    lang_names = {"ceb": "Cebuano"}
    print(f"\nGenerating TTS text: {stem} ({lang_names[language]})")

    markdown_script = (output_dir / f"{stem}_radio_{language}.md").read_text(encoding="utf-8")

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": TTS_PROMPTS[language]["system"]},
            {"role": "user", "content": build_tts_prompt(markdown_script, language)},
        ],
        "stream": False,
    }

    t_start = time.time()
    response = requests.post(f"{OLLAMA_API}/api/chat", json=payload, timeout=TIMEOUT)
    elapsed = time.time() - t_start

    tts_text = response.json().get("message", {}).get("content", "").strip()

    out_path = output_dir / f"{stem}_tts_{language}.txt"
    out_path.write_text(tts_text, encoding="utf-8")

    word_count = len(tts_text.split())
    print(f"  ✓ Generated in {elapsed:.1f}s")
    print(f"  Words: {word_count}")
    print(f"  Saved → {out_path.name}")

    return {
        "stem": stem,
        "language": language,
        "tts_text": tts_text,
        "word_count": word_count,
        "elapsed": elapsed,
    }


# Generate TTS text for both bulletins — CEB only
tts_results = []
for bulletin in bulletins:
    result = generate_tts_text(bulletin, "ceb")
    tts_results.append(result)

print(f"\n✓ Done — {len(tts_results)} TTS text files generated")

# Preview first bulletin
print("\nPREVIEW — CEB TTS text (first 500 chars)")
print("=" * 60)
print(tts_results[0]["tts_text"][:500])
print("...")
```

- [ ] **Step 4: Run the 3 new cells and verify output files exist**

Run only the 3 newly inserted cells (prior cells already have output from the previous run).

Then verify:
```bash
ls /Users/josereyes/Dev/gemma4-hackathon/data/radio_bulletins/*_tts_ceb.txt
```

Expected:
```
.../PAGASA_20-19W_Pepito_SWB#01_tts_ceb.txt
.../PAGASA_22-TC02_Basyang_TCA#01_tts_ceb.txt
```

- [ ] **Step 5: Commit**

```bash
cd /Users/josereyes/Dev/gemma4-hackathon && git add notebooks/06-radio-bulletin.ipynb && git commit -m "feat: add TTS plain text generation in notebook 06 (CEB, dialect-pure)"
```

---

### Task 4: Notebook 08 — update pipeline to sentence-level synthesis

**Files:**
- Modify: `notebooks/08-mms-tts-experiment.ipynb`

Three cells need updating. Use `NotebookEdit` to edit each by cell source match.

- [ ] **Step 1: Update setup cell `7abe84e4` — read `_tts_{lang}.txt` instead of `_radio_{lang}.md`**

In cell `7abe84e4`, make two changes:

Change `input_files` assignment:
```python
# OLD
input_files = {lang: input_dir / f"{STEM}_radio_{lang}.md" for lang in LANGUAGES}
# NEW
input_files = {lang: input_dir / f"{STEM}_tts_{lang}.txt" for lang in LANGUAGES}
```

Change the `raise FileNotFoundError` message:
```python
# OLD
raise FileNotFoundError(f"Required input files not found. Generate them in notebook 06 first.")
# NEW
raise FileNotFoundError(f"Required TTS text files not found. Run notebook 06 TTS generation cells first.")
```

- [ ] **Step 2: Replace preprocessing cell `38715dd2` — swap `preprocess_for_tts` for `prepare_mms_sentences`**

Replace the entire source of cell `38715dd2` with:

```python
import re


def prepare_mms_sentences(text: str) -> list[tuple[str, bool]]:
    """Split plain text into MMS-ready sentences with paragraph boundary flags.

    Returns list of (sentence, is_paragraph_end) tuples where:
    - sentence: lowercase, punctuation-stripped (in-word apostrophes/hyphens preserved)
    - is_paragraph_end: True if last sentence of its paragraph (triggers longer pause)
    """
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    result = []
    for paragraph in paragraphs:
        sentences = re.split(r'(?<=[.!?])\s+', paragraph)
        sentences = [s.strip() for s in sentences if s.strip()]
        for sent_idx, sentence in enumerate(sentences):
            is_last_in_para = (sent_idx == len(sentences) - 1)
            sentence = sentence.lower()
            # Remove all punctuation except apostrophes and hyphens
            s = re.sub(r"[^\w\s'\-]", " ", sentence)
            # Remove apostrophes/hyphens not flanked by word characters (standalone)
            s = re.sub(r"(?<!\w)['\-]|['\-](?!\w)", " ", s)
            sentence = re.sub(r"\s+", " ", s).strip()
            if sentence:
                result.append((sentence, is_last_in_para))
    return result


# Prepare sentences for all scripts
sentence_lists = {}
for lang in LANGUAGES:
    text = input_files[lang].read_text(encoding="utf-8")
    sentences = prepare_mms_sentences(text)
    sentence_lists[lang] = sentences
    print(f"✓ {lang}: {len(sentences)} sentences from {len(text)} chars")
    print(f"  First: {sentences[0][0][:80]!r}  (para_end={sentences[0][1]})")
    print(f"  Last:  {sentences[-1][0][:80]!r}  (para_end={sentences[-1][1]})")
```

Also replace the markdown cell `b37749cc` source (the heading for section 1) with:

```markdown
## 1. Prepare Sentences for MMS

Split the TTS plain text into individual sentences using `prepare_mms_sentences`.
Each sentence is lowercased and stripped of punctuation (MMS TTS hard requirements).
Paragraph boundaries are flagged to control silence pause duration during stitching.

**Pause timings:** 500ms between sentences, 750ms between paragraphs.

Input: `data/radio_bulletins/{stem}_tts_{lang}.txt`
```

- [ ] **Step 3: Replace synthesis cell `a295e144` — new `synthesize_with_mms` + updated call**

Replace the entire source of cell `a295e144` with:

```python
def synthesize_with_mms(
    sentences: list[tuple[str, bool]],
    model,
    tokenizer,
    output_path: Path,
    sample_rate: int | None = None,
    sentence_pause_ms: int = 500,
    paragraph_pause_ms: int = 750,
) -> Path:
    """Synthesize sentence list to MP3 with silence stitching.

    Modal-ready: all inputs are primitive types + Path; no notebook globals.

    Args:
        sentences: List of (sentence, is_paragraph_end) from prepare_mms_sentences().
        model: Loaded VitsModel instance.
        tokenizer: Loaded AutoTokenizer instance.
        output_path: Destination MP3 path.
        sample_rate: Override model's native sample rate if needed.
        sentence_pause_ms: Silence after each non-final sentence in a paragraph (ms).
        paragraph_pause_ms: Silence after the last sentence of each paragraph (ms).

    Returns:
        output_path on success.
    """
    rate = sample_rate or model.config.sampling_rate
    combined = AudioSegment.empty()
    for sentence, is_paragraph_end in sentences:
        if not sentence.strip():
            continue
        inputs = tokenizer(sentence, return_tensors="pt")
        with torch.no_grad():
            waveform = model(**inputs).waveform
        pcm = (waveform.squeeze().numpy() * 32_767).clip(-32_768, 32_767).astype(np.int16)
        segment = AudioSegment(pcm.tobytes(), frame_rate=rate, sample_width=2, channels=1)
        combined += segment
        pause_ms = paragraph_pause_ms if is_paragraph_end else sentence_pause_ms
        combined += AudioSegment.silent(duration=pause_ms, frame_rate=rate)
    combined.export(str(output_path), format="mp3", bitrate="128k")
    return output_path


# --- Run synthesis: CEB → MP3 ---
results = {}

for lang in LANGUAGES:
    lang_label = {"ceb": "Cebuano", "tl": "Tagalog", "en": "English"}[lang]
    output_path = output_dir / f"{STEM}_tts_{lang}.mp3"

    sentences = sentence_lists[lang]
    print(f"Synthesizing {lang_label} ({len(sentences)} sentences)...")
    t_start = time.time()
    synthesize_with_mms(
        sentences,
        models[lang],
        tokenizers[lang],
        output_path,
    )
    elapsed = time.time() - t_start

    size_kb = output_path.stat().st_size // 1024
    duration_s = (size_kb * 1024 * 8) / 128_000

    print(f"  ✓ {elapsed:.1f}s  |  {size_kb} KB  |  ~{duration_s:.0f}s audio")
    print(f"  ✓ {output_path.name}")

    results[lang] = {
        "lang_label": lang_label,
        "elapsed_s": round(elapsed, 1),
        "size_kb": size_kb,
        "duration_s": round(duration_s),
        "path": output_path,
    }

print("\n✓ Synthesis complete")
```

Also replace the markdown cell `5c890df5` source with:

```markdown
## 3. Synthesis

`synthesize_with_mms` processes sentences one at a time:
1. Tokenize → model inference → float32 waveform
2. Convert to int16 PCM → pydub AudioSegment
3. Append silence: 500ms between sentences, 750ms after paragraph-final sentences
4. Concatenate all segments → export MP3 at 128kbps

Output: `notebooks/08-mms-tts-experiment/{stem}_tts_{lang}.mp3`
```

- [ ] **Step 4: Run notebook 08 cells in order and verify**

Run cells in this sequence:
1. Setup cell `7abe84e4` — expected: `✓ All 1 input file(s) found` showing `_tts_ceb.txt`
2. Preprocessing cell `38715dd2` — expected: `✓ ceb: N sentences from M chars`
3. Load models cell `49df8a25` — expected: models load from cache
4. Synthesis cell `a295e144` — expected: `Synthesizing Cebuano (N sentences)...` then `✓ ~Xs`

Verify the output MP3 exists:
```bash
ls /Users/josereyes/Dev/gemma4-hackathon/notebooks/08-mms-tts-experiment/*_tts_ceb.mp3
```

- [ ] **Step 5: Commit**

```bash
cd /Users/josereyes/Dev/gemma4-hackathon && git add notebooks/08-mms-tts-experiment.ipynb && git commit -m "feat: update notebook 08 to sentence-level synthesis with silence stitching"
```

---

### Task 5: Push branch

**Files:** none

- [ ] **Step 1: Run full test suite**

```bash
cd /Users/josereyes/Dev/gemma4-hackathon && uv run pytest tests/ -v
```

Expected: All 13 tests pass.

- [ ] **Step 2: Push feature branch to remote**

```bash
cd /Users/josereyes/Dev/gemma4-hackathon && git push -u origin feature/tts-experiment
```

Expected: Branch pushed. No force push needed — this is an existing remote branch.
