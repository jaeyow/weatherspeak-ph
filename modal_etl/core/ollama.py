import re
import time

import requests


def wait_for_ollama(url: str, retries: int = 60, delay: float = 2.0) -> None:
    """Block until Ollama responds on /api/tags or raise RuntimeError."""
    for _ in range(retries):
        try:
            requests.get(f"{url}/api/tags", timeout=5)
            return
        except (requests.exceptions.ConnectionError, requests.exceptions.ReadTimeout):
            time.sleep(delay)
    raise RuntimeError(f"Ollama at {url} did not respond within timeout")


def call_ollama_generate(
    url: str,
    model: str,
    prompt: str,
    system: str | None = None,
    images_b64: list[str] | None = None,
    fmt: dict | None = None,
    timeout: int = 600,
) -> str:
    """POST /api/generate and return the response text."""
    payload: dict = {"model": model, "prompt": prompt, "stream": False}
    if system:
        payload["system"] = system
    if images_b64:
        payload["images"] = images_b64
    if fmt:
        payload["format"] = fmt
    resp = requests.post(f"{url}/api/generate", json=payload, timeout=timeout)
    resp.raise_for_status()
    return resp.json()["response"]


def call_ollama_chat(
    url: str,
    model: str,
    system: str,
    user: str,
    timeout: int = 300,
) -> str:
    """POST /api/chat and return the assistant message, stripped of <think> blocks."""
    resp = requests.post(
        f"{url}/api/chat",
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
        },
        timeout=timeout,
    )
    resp.raise_for_status()
    content = resp.json()["message"]["content"].strip()
    content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
    return content
