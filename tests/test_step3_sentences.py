from modal_etl.core.tts import prepare_mms_sentences, prepare_english_sentences


# --- prepare_mms_sentences (for CEB/TL) ---

def test_mms_single_sentence():
    assert prepare_mms_sentences("Hello world.") == [("hello world", True)]


def test_mms_multi_sentence_paragraph():
    result = prepare_mms_sentences("Maayong buntag. Pag-andam na mo.")
    assert result == [("maayong buntag", False), ("pag-andam na mo", True)]


def test_mms_two_paragraphs():
    result = prepare_mms_sentences("First sentence.\n\nSecond sentence.")
    assert result == [("first sentence", True), ("second sentence", True)]


def test_mms_apostrophe_in_word_preserved():
    result = prepare_mms_sentences("Mo'y dako kaayo.")
    assert result[0][0] == "mo'y dako kaayo"


def test_mms_standalone_quotes_stripped():
    result = prepare_mms_sentences("'Hello world'.")
    assert result[0][0] == "hello world"


def test_mms_em_dash_stripped():
    result = prepare_mms_sentences("Ang bagyo—mabilis.")
    assert result[0][0] == "ang bagyo mabilis"


def test_mms_fully_lowercase_no_punctuation():
    result = prepare_mms_sentences("PAGASA Signal Number TWO warns!")
    assert result[0][0] == "pagasa signal number two warns"


# --- prepare_english_sentences (for EN) ---

def test_english_preserves_capitalisation():
    result = prepare_english_sentences("Tropical Depression Pepito.")
    assert result[0][0] == "Tropical Depression Pepito."


def test_english_preserves_punctuation():
    result = prepare_english_sentences("Winds of 85 kph. Expect heavy rainfall.")
    assert "." in result[0][0]


def test_english_two_paragraphs():
    result = prepare_english_sentences("First para.\n\nSecond para.")
    assert result[0] == ("First para.", True)
    assert result[1] == ("Second para.", True)


def test_english_multi_sentence_paragraph():
    result = prepare_english_sentences("Stay indoors. Avoid flooded areas.")
    assert len(result) == 2
    assert result[0][1] is False   # not paragraph end
    assert result[1][1] is True    # paragraph end
