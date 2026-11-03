"""Thin, provider-agnostic wrapper around a hosted language model (plain HTTP, no SDK needed).

Error reporting rules (see tests/test_core.py::TestLLMErrors):
  * every failure becomes an ``LLMError`` whose text says what happened in plain words;
  * HTTP failures include the real status code and the provider's own message;
  * API keys are never put in a URL, never logged and are scrubbed from every message.
The callers (extract.py, paste.py) catch ``LLMError`` and fall back to the offline extractor.
"""
from __future__ import annotations
import logging
import os
import re
import sys
import time

import requests

from . import config

log = logging.getLogger("handovertrail.llm")

KEY_VARS = {"anthropic": "ANTHROPIC_API_KEY", "openai": "OPENAI_API_KEY", "gemini": "GEMINI_API_KEY"}
PROVIDER_NAME = {"anthropic": "Anthropic", "openai": "OpenAI", "gemini": "Google Gemini"}
RETRY_STATUS = (429, 500, 503)
MAX_DETAIL = 300


class LLMError(Exception):
    """A readable, key-free explanation. ``status_code`` is set for HTTP failures."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


def available(provider=None) -> bool:
    p = provider or config.llm_provider()
    return p in KEY_VARS and bool(os.environ.get(KEY_VARS[p]))


# ------------------------------------------------------------------ keeping keys out of text
_KEY_PATTERNS = [
    re.compile(r"AIza[0-9A-Za-z_\-]{20,}"),            # Google API keys
    re.compile(r"sk-[A-Za-z0-9_\-]{16,}"),             # OpenAI / Anthropic style keys
    re.compile(r"(?i)([?&]key=)[^&\s\"']+"),           # key=... in a URL
    re.compile(r"(?i)(x-goog-api-key|x-api-key|authorization)(['\"]?\s*[:=]\s*['\"]?)(Bearer\s+)?[^\s,'\"}]+"),
]


def scrub(text) -> str:
    """Remove any API key (the real ones from the environment, or anything shaped like one)."""
    s = str(text)
    for var in KEY_VARS.values():
        v = os.environ.get(var, "")
        if len(v) >= 6:
            s = s.replace(v, "[hidden key]")
    s = _KEY_PATTERNS[0].sub("[hidden key]", s)
    s = _KEY_PATTERNS[1].sub("[hidden key]", s)
    s = _KEY_PATTERNS[2].sub(r"\1[hidden key]", s)
    s = _KEY_PATTERNS[3].sub(lambda m: f"{m.group(1)}{m.group(2)}[hidden key]", s)
    return s


def _env(name: str, provider: str) -> str:
    v = os.environ.get(name, "").strip()
    if not v:
        raise LLMError(f"Missing setting {name} for provider '{provider}'. Add it to your .env file.")
    return v


# ------------------------------------------------------------------ reading HTTP errors
def _error_body(r) -> tuple[str, str]:
    """Return (provider_status_label, message) from an error response. Never raises."""
    label, message = "", ""
    try:
        data = r.json()
        if isinstance(data, list) and data:          # Google sometimes wraps the error in a list
            data = data[0]
        err = data.get("error") if isinstance(data, dict) else None
        if isinstance(err, dict):
            label = str(err.get("status") or err.get("type") or err.get("code") or "")
            message = str(err.get("message") or "")
        elif isinstance(err, str):
            message = err
    except Exception:
        pass
    if not message:
        try:
            message = (getattr(r, "text", "") or "").strip()
        except Exception:
            message = ""
    message = " ".join(scrub(message).split())
    if len(message) > MAX_DETAIL:
        message = message[:MAX_DETAIL].rstrip() + "..."
    return label, message


def _hint(status: int, provider: str, model: str, message: str) -> str:
    env_model = f"{provider.upper()}_MODEL"
    key_var = KEY_VARS.get(provider, "the API key")
    low = message.lower()
    if status == 400:
        if "api key" in low and ("not valid" in low or "invalid" in low or "expired" in low):
            return f"The API key was refused as invalid or expired. Check {key_var} in your .env file."
        if "location" in low or "region" in low:
            return "The service is not available for your location or account region."
        if "billing" in low or "precondition" in low:
            return "The account is not set up for this request (billing or free tier not available here)."
        return (f"The request was rejected as invalid. Common causes: a wrong model setting "
                f"({env_model}={model}), an unsupported option, or input that is too large.")
    if status == 401:
        return f"The API key is missing, wrong or expired. Check {key_var} in your .env file."
    if status == 403:
        return ("The key was recognised but is not allowed to do this: the API may not be enabled for the "
                "project, the key may be restricted or revoked, or the region/account is not supported.")
    if status == 404:
        return f"The model '{model}' was not found. Check {env_model} in your .env file for typos or retired names."
    if status == 429:
        return "Too many requests or the quota is used up. Wait a minute and try again, or check your plan/quota."
    if status == 500:
        return "The AI service had an internal error. This is usually temporary; try again shortly."
    if status == 503:
        return "The AI service is overloaded or unavailable right now. This is usually temporary; try again shortly."
    if status >= 500:
        return "The AI service had a server-side problem. Try again shortly."
    return "The AI service refused the request."


def http_error(r, provider: str, model: str) -> LLMError:
    status = int(r.status_code)
    label, message = _error_body(r)
    name = PROVIDER_NAME.get(provider, provider)
    head = f"{name} API error {status}" + (f" ({label})" if label else "")
    text = f"{head}: {_hint(status, provider, model, message)}"
    if message:
        text += f' {name.split()[-1]} said: "{message}"'
    log.warning("LLM HTTP error provider=%s model=%s status=%s label=%s detail=%s",
                provider, model, status, label, message)
    return LLMError(scrub(text), status_code=status)


def _post(url: str, provider: str = "", model: str = "", **kw):
    """POST with polite retries for rate limits (429) and temporary server errors (500/503)."""
    delay = 3
    for attempt in range(4):
        r = requests.post(url, **kw)
        if r.status_code in RETRY_STATUS and attempt < 3:
            log.info("LLM %s returned %s; retrying in %ss", provider, r.status_code, delay)
            time.sleep(delay)
            delay *= 2
            continue
        if r.status_code >= 400:
            raise http_error(r, provider, model)
        return r
    raise LLMError("The AI service kept refusing the request. Wait a minute and try again.")


def _gemini_text(data: dict) -> str:
    cands = data.get("candidates") or []
    if not cands:
        reason = (data.get("promptFeedback") or {}).get("blockReason")
        raise LLMError("Google Gemini returned no answer" +
                       (f" (the prompt was blocked: {reason})." if reason else "."))
    cand = cands[0]
    parts = (cand.get("content") or {}).get("parts") or []
    text = "".join(p.get("text", "") for p in parts if isinstance(p, dict))
    if not text:
        raise LLMError(f"Google Gemini returned an empty answer (finishReason: {cand.get('finishReason', 'unknown')}).")
    return text


def complete(system: str, user: str, provider=None, timeout: int = 90) -> str:
    p = provider or config.llm_provider()
    try:
        if p == "anthropic":
            key = _env("ANTHROPIC_API_KEY", p)
            model = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5-5")
            r = _post("https://api.anthropic.com/v1/messages", p, model, timeout=timeout,
                      headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                               "content-type": "application/json"},
                      json={"model": model, "max_tokens": 4000, "temperature": 0, "system": system,
                            "messages": [{"role": "user", "content": user}]})
            return "".join(b.get("text", "") for b in r.json()["content"])
        if p == "openai":
            key = _env("OPENAI_API_KEY", p)
            model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
            r = _post("https://api.openai.com/v1/chat/completions", p, model, timeout=timeout,
                      headers={"Authorization": f"Bearer {key}"},
                      json={"model": model, "temperature": 0,
                            "messages": [{"role": "system", "content": system},
                                         {"role": "user", "content": user}]})
            return r.json()["choices"][0]["message"]["content"]
        if p == "gemini":
            key = _env("GEMINI_API_KEY", p)
            model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash-lite").strip()
            # The key goes in a header, never in the URL, so it cannot leak through error text or logs.
            r = _post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                      p, model, timeout=timeout,
                      headers={"x-goog-api-key": key, "content-type": "application/json"},
                      json={"systemInstruction": {"parts": [{"text": system}]},
                            "contents": [{"role": "user", "parts": [{"text": user}]}],
                            "generationConfig": {"temperature": 0, "responseMimeType": "application/json"}})
            return _gemini_text(r.json())
    except LLMError:
        raise
    except requests.Timeout as e:
        raise LLMError(f"The AI service did not answer within {timeout} seconds ({type(e).__name__}). "
                       "Try again, or check your internet connection.") from None
    except requests.exceptions.SSLError as e:
        raise LLMError("A secure connection to the AI service could not be made (SSLError). "
                       "Check your date/time, proxy or network.") from None
    except requests.ConnectionError as e:
        raise LLMError("The AI service could not be reached (ConnectionError). "
                       "Check your internet connection, VPN or firewall.") from None
    except requests.RequestException as e:
        raise LLMError(f"The AI service could not be reached ({type(e).__name__}).") from None
    except (ValueError, IndexError, KeyError, TypeError, AttributeError):
        raise LLMError("The AI service returned an unexpected response.") from None
    raise LLMError(f"Unknown LLM_PROVIDER '{p}'. Use offline, anthropic, openai or gemini.")


# ------------------------------------------------------------------ connection self-test
def _list_gemini_models() -> int:
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        print("GEMINI_API_KEY is not set (check your .env file).")
        return 2
    try:
        r = requests.get("https://generativelanguage.googleapis.com/v1beta/models",
                         headers={"x-goog-api-key": key}, params={"pageSize": 200}, timeout=30)
    except requests.RequestException as e:
        print(f"Could not reach Google ({type(e).__name__}).")
        return 1
    if r.status_code >= 400:
        print(http_error(r, "gemini", os.environ.get("GEMINI_MODEL", "")))
        return 1
    for m in r.json().get("models", []):
        if "generateContent" in m.get("supportedGenerationMethods", []):
            print(m.get("name", "").replace("models/", ""))
    return 0


def self_test(provider=None) -> int:
    p = provider or config.llm_provider()
    if p == "offline":
        print("LLM_PROVIDER is 'offline': nothing to test. Set LLM_PROVIDER=gemini in .env.")
        return 2
    if p not in KEY_VARS:
        print(f"Unknown LLM_PROVIDER '{p}'. Use offline, anthropic, openai or gemini.")
        return 2
    model = os.environ.get(f"{p.upper()}_MODEL", "(default)")
    print(f"Provider: {p}\nModel:    {model}\nAPI key:  {'found' if available(p) else 'MISSING'}")
    try:
        out = complete("Reply with JSON only.", 'Return exactly {"ok": true}', p, timeout=30)
    except LLMError as e:
        print(f"\nFAILED: {e}")
        return 1
    print(f"\nOK - the {p} connection works. Model replied: {scrub(out).strip()[:80]}")
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    if "--models" in sys.argv:
        sys.exit(_list_gemini_models())
    sys.exit(self_test())
