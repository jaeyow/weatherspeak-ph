"""Tests for modal_etl/core/ollama.py."""
import pytest
from unittest.mock import patch, MagicMock
from modal_etl.core.ollama import wait_for_ollama, call_ollama_generate, call_ollama_chat


def test_wait_for_ollama_raises_when_server_unreachable():
    """wait_for_ollama raises RuntimeError after exhausting retries."""
    import requests
    with patch("modal_etl.core.ollama.requests.get", side_effect=requests.exceptions.ConnectionError):
        with patch("modal_etl.core.ollama.time.sleep"):
            with pytest.raises(RuntimeError, match="did not respond"):
                wait_for_ollama("http://localhost:11434", retries=2, delay=0.0)


def test_wait_for_ollama_returns_when_server_ready():
    """wait_for_ollama returns normally when server responds."""
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    with patch("modal_etl.core.ollama.requests.get", return_value=mock_resp):
        wait_for_ollama("http://localhost:11434", retries=1, delay=0.0)


def test_call_ollama_generate_sends_correct_payload():
    """call_ollama_generate POSTs to /api/generate with expected fields."""
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"response": "test output"}
    with patch("modal_etl.core.ollama.requests.post", return_value=mock_resp) as mock_post:
        result = call_ollama_generate(
            url="http://localhost:11434",
            model="gemma4:e4b",
            prompt="test prompt",
            system="test system",
        )
    assert result == "test output"
    payload = mock_post.call_args.kwargs["json"]
    assert payload["model"] == "gemma4:e4b"
    assert payload["prompt"] == "test prompt"
    assert payload["system"] == "test system"
    assert payload["stream"] is False


def test_call_ollama_generate_includes_images_when_provided():
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"response": "ok"}
    with patch("modal_etl.core.ollama.requests.post", return_value=mock_resp) as mock_post:
        call_ollama_generate(
            url="http://localhost:11434",
            model="gemma4:e4b",
            prompt="describe image",
            images_b64=["abc123"],
        )
    payload = mock_post.call_args.kwargs["json"]
    assert payload["images"] == ["abc123"]


def test_call_ollama_chat_strips_think_blocks():
    """call_ollama_chat removes <think>...</think> from the response."""
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "message": {"content": "<think>internal reasoning</think>The actual answer."}
    }
    with patch("modal_etl.core.ollama.requests.post", return_value=mock_resp):
        result = call_ollama_chat(
            url="http://localhost:11434",
            model="gemma4:e4b",
            system="you are helpful",
            user="what is 2+2",
        )
    assert result == "The actual answer."
    assert "<think>" not in result


def test_call_ollama_chat_sends_chat_messages():
    """call_ollama_chat POSTs to /api/chat with system + user messages."""
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"message": {"content": "response"}}
    with patch("modal_etl.core.ollama.requests.post", return_value=mock_resp) as mock_post:
        call_ollama_chat(
            url="http://localhost:11434",
            model="gemma4:e4b",
            system="sys",
            user="usr",
        )
    payload = mock_post.call_args.kwargs["json"]
    assert payload["messages"][0] == {"role": "system", "content": "sys"}
    assert payload["messages"][1] == {"role": "user", "content": "usr"}
