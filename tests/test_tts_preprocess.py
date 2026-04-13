import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Inline implementation (copy from notebook once both are in sync)
# ---------------------------------------------------------------------------

def preprocess_for_tts(markdown_text: str) -> str:
    """Strip markdown formatting and insert pause cues at section boundaries."""
    text = markdown_text

    # Section headings → pause cue + heading text as a spoken sentence
    text = re.sub(r"^#{1,6}\s+(.+)$", r"\n...\n\1.\n", text, flags=re.MULTILINE)

    # Bold and italic markers
    text = re.sub(r"\*{1,3}(.+?)\*{1,3}", r"\1", text)
    text = re.sub(r"_{1,3}(.+?)_{1,3}", r"\1", text)

    # Inline code
    text = re.sub(r"`(.+?)`", r"\1", text)

    # Blockquotes
    text = re.sub(r"^>\s+", "", text, flags=re.MULTILINE)

    # Horizontal rules
    text = re.sub(r"^[-*_]{3,}$", "", text, flags=re.MULTILINE)

    # Collapse 3+ blank lines to 2
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_strips_headings_and_adds_pause_cue():
    md = "## Forecast Track\n\nSome text."
    result = preprocess_for_tts(md)
    assert "##" not in result
    assert "..." in result
    assert "Forecast Track." in result
    assert "Some text." in result


def test_strips_bold_markers():
    md = "**Typhoon PEPITO** is moving west."
    result = preprocess_for_tts(md)
    assert "**" not in result
    assert "Typhoon PEPITO is moving west." in result


def test_strips_italic_markers():
    md = "*signal number two* is in effect."
    result = preprocess_for_tts(md)
    assert "*" not in result
    assert "signal number two is in effect." in result


def test_collapses_multiple_blank_lines():
    md = "Line one.\n\n\n\nLine two."
    result = preprocess_for_tts(md)
    assert "\n\n\n" not in result


def test_strips_inline_code():
    md = "Use `gemma4:e4b` for inference."
    result = preprocess_for_tts(md)
    assert "`" not in result
    assert "gemma4:e4b" in result


def test_strips_blockquote():
    md = "> Note: this is a note."
    result = preprocess_for_tts(md)
    assert result.startswith(">") is False
    assert "Note: this is a note." in result


def test_output_has_no_leading_trailing_whitespace():
    md = "\n\n## Title\n\nContent.\n\n"
    result = preprocess_for_tts(md)
    assert result == result.strip()


def test_pause_cue_position():
    """Pause cue (...) must appear BEFORE the heading text, not after."""
    md = "## Current Situation\n\nResidents are urged..."
    result = preprocess_for_tts(md)
    ellipsis_pos = result.index("...")
    heading_pos = result.index("Current Situation.")
    assert ellipsis_pos < heading_pos


if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    passed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL  {t.__name__}: {e}")
    print(f"\n{passed}/{len(tests)} passed")
