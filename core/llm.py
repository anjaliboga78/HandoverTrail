"""Thin, provider-agnostic wrapper around a hosted language model (plain HTTP, no SDK needed)."""
from __future__ import annotations
import os
import time

import requests

from . import config


class LLMError(Exception):
    pass


def available(provider=None) -> bool:
    p = provider or config.llm_provider()
    keys = {"anthropic": "ANTHROPIC_API_KEY", "openai": "OPENAI_API_KEY", "gemini": "GEMINI_API_KEY"}
    return p in keys and bool(os.environ.get(keys[p]))


def _post(url: str, **kw):
    """POST with polite retries for rate limits (429) and temporary server errors."""
    delay = 3
    for attempt in range(4):
        r = requests.post(url, **kw)
        if r.status_code in (429, 500, 503) and attempt < 3:
            time.sleep(delay)
            delay *= 2
            continue
        r.raise_for_status()
        return r
    raise LLMError("The AI service kept refusing the request (rate limit). Wait a minute and try again.")


def complete(system: str, user: str, provider=None, timeout: int = 90) -> str:
    p = provider or config.llm_provider()
    try:
        if p == "anthropic":
            key = os.environ["ANTHROPIC_API_KEY"]
            model = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5-5")
            r = _post("https://api.anthropic.com/v1/messages", timeout=timeout,
                      headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                               "content-type": "application/json"},
                      json={"model": model, "max_tokens": 4000, "temperature": 0, "system": system,
                            "messages": [{"role": "user", "content": user}]})
            return "".join(b.get("text", "") for b in r.json()["content"])
        if p == "openai":
            key = os.environ["OPENAI_API_KEY"]
            model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
            r = _post("https://api.openai.com/v1/chat/completions", timeout=timeout,
                      headers={"Authorization": f"Bearer {key}"},
                      json={"model": model, "temperature": 0,
                            "messages": [{"role": "system", "content": system},
                                         {"role": "user", "content": user}]})
            return r.json()["choices"][0]["message"]["content"]
        if p == "gemini":
            key = os.environ["GEMINI_API_KEY"]
            model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash-lite")
            r = _post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                      params={"key": key}, timeout=timeout,
                      json={"systemInstruction": {"parts": [{"text": system}]},
                            "contents": [{"role": "user", "parts": [{"text": user}]}],
                            "generationConfig": {"temperature": 0, "responseMimeType": "application/json"}})
            return r.json()["candidates"][0]["content"]["parts"][0]["text"]
    except KeyError as e:
        raise LLMError(f"Missing setting for provider '{p}': {e}. Check your .env file.") from e
    except requests.RequestException as e:
        raise LLMError(f"The AI service could not be reached ({type(e).__name__}).") from e
    except (ValueError, IndexError) as e:
        raise LLMError("The AI service returned an unexpected response.") from e
    raise LLMError(f"Unknown LLM_PROVIDER '{p}'. Use offline, anthropic, openai or gemini.")
