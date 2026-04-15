# TTS Pipeline — Dialect-Pure Text Generation Design

**Date:** 2026-04-15
**Branch:** `feature/tts-experiment`
**Author:** Jose Reyes

---

## Problem

The current TTS pipeline generates a markdown radio script in notebook 06, then strips
that markdown in notebook 08 (`preprocess_for_tts`) to produce plain text for synthesis.
This is wasteful — markdown is generated only to be stripped. Worse, the resulting plain
text contains English words that MMS TTS mispronounces in Filipino dialects.

Additionally, MMS TTS has two hard requirements the current pipeline ignores:
1. All input must be **lowercase**
2. Input must have **no punctuation**

---

## Goals

1. Produce a dialect-pure, TTS-ready plain text file directly from the radio script markdown
   (via a second Gemma4 prompt in notebook 06) — no markdown stripping step needed
2. Implement sentence-level synthesis with silence stitching for natural pauses
3. Enable read-along UX: TTS text mirrors the markdown so users can follow on screen

---

## Scope

Cebuano (`ceb`) only. TL and EN will follow the same pattern once CEB is validated.

---

## Pipeline Change

### Before

```
PAGASA bulletin markdown (nb04)
  → Gemma4 (nb06): markdown radio script → data/radio_bulletins/{stem}_radio_ceb.md
  → preprocess_for_tts (nb08): strip markdown → plain text
  → synthesize_with_mms (nb08): full text → MP3
```

### After

```
PAGASA bulletin markdown (nb04)
  → Gemma4 (nb06): markdown radio script → data/radio_bulletins/{stem}_radio_ceb.md  [for frontend]
  → Gemma4 (nb06): TTS plain text       → data/radio_bulletins/{stem}_tts_ceb.txt   [for audio]
       ↓
  → prepare_mms_sentences (nb08): split + lowercase + strip punctuation → sentence list
  → synthesize_with_mms (nb08): sentence list + silence → MP3
```

---

## Notebook 06 Change

### New Gemma4 prompt (per language, after markdown generation)

**Input:** The generated markdown radio script (`{stem}_radio_{lang}.md`)

**Prompt instructions to Gemma4:**
- Rewrite the script as flowing plain prose — no markdown, no headings, no bullet points,
  no bold, no asterisks, no dashes used as formatting
- Use **only words from the target language** (Cebuano for `ceb`)
- For unavoidable proper nouns or English technical terms, **phonetically spell them** in
  the target language's phoneme system
  - Examples for Cebuano: `PAGASA` → `pa-ga-sa`, `Northern Luzon` → `nor-dern lu-zon`,
    `tropical depression` → `tro-pi-kal di-pre-syon`
- Preserve paragraph structure (blank lines between paragraphs) — this drives pause timing
- Do not add any text that wasn't in the original script

**Output:** Saved to `data/radio_bulletins/{stem}_tts_{lang}.txt`

---

## Notebook 08 Changes

### New function: `prepare_mms_sentences(text) -> list[tuple[str, bool]]`

Takes the plain text from `{stem}_tts_{lang}.txt` and returns a list of
`(sentence, is_paragraph_end)` tuples.

**Steps:**
1. Split on blank lines (`\n\n`) to identify paragraph boundaries
2. Within each paragraph, split on sentence-ending punctuation: `.` `!` `?`
3. Lowercase each sentence
4. Strip all punctuation characters — **except** apostrophes within words
   (e.g., `mo'y` stays `mo'y`; standalone `"` or `'` are stripped)
5. Strip leading/trailing whitespace from each sentence
6. Filter empty strings
7. Mark the last sentence of each paragraph with `is_paragraph_end=True`;
   all others `False`

**Returns:** `list[tuple[str, bool]]`
- `str`: lowercase, punctuation-stripped sentence
- `bool`: `True` if this is the last sentence of its paragraph (longer pause follows)

### Updated function: `synthesize_with_mms`

**New signature:**
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
```

**Behaviour:**
- For each `(sentence, is_paragraph_end)` tuple:
  - Tokenize and synthesize the sentence → waveform
  - Convert float32 waveform → int16 PCM → `AudioSegment`
  - Append `AudioSegment.silent(duration=paragraph_pause_ms)` if `is_paragraph_end=True`
  - Append `AudioSegment.silent(duration=sentence_pause_ms)` otherwise
- Concatenate all segments → export MP3 at 128kbps

**Note:** `preprocess_for_tts` is no longer called in notebook 08. The `.txt` file is
already plain text; `prepare_mms_sentences` handles all remaining normalization.

---

## Pause Timings

| Boundary | Duration |
|---|---|
| Between sentences within a paragraph | 500ms |
| Between paragraphs | 750ms |

---

## File Naming

| File | Description |
|---|---|
| `data/radio_bulletins/{stem}_radio_{lang}.md` | Markdown radio script (existing, unchanged) |
| `data/radio_bulletins/{stem}_tts_{lang}.txt` | TTS-optimized plain text (new) |
| `data/tts_output/{stem}_tts_{lang}.mp3` | Synthesized MP3 (nb08 output) |

---

## Tests

New tests in `tests/test_mms_synthesis.py` for `prepare_mms_sentences`:

| Test | What it verifies |
|---|---|
| Single sentence | Returns one tuple, `is_paragraph_end=True` |
| Multi-sentence paragraph | Correct split, all lowercase, no punctuation, last sentence flagged |
| Two paragraphs | Paragraph boundary correctly flagged on last sentence of first paragraph |
| Em-dash mid-sentence | `—` treated as sentence separator or stripped, not kept |
| Apostrophe in word | `mo'y` preserved; standalone quotes stripped |
| Mixed case + punctuation | Output is fully lowercase, punctuation stripped |

Updated mock-based tests for `synthesize_with_mms` to reflect new signature
(list of tuples instead of single string).

---

## Out of Scope

- TL and EN language support (follow-on work once CEB is validated)
- Changes to notebooks 01–05
- Frontend read-along synchronization (separate feature)
- Phonetic spelling dictionary/lookup table (Gemma4 handles this in the prompt)
