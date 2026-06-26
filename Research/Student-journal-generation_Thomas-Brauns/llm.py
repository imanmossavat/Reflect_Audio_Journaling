"""
llm.py — Shared LLM client
============================
Single call_llm() function used by all pipeline stages.
Supports Ollama (local) and Anthropic API backends,
controlled by BACKEND in config.py.

Retry logic is built in: on JSON parse failure the call is retried
up to MAX_RETRIES times before raising.

Usage:
    from llm import call_llm
    raw_text = call_llm(prompt, stage="stage_01")
"""

import json
import re
import time

import config


def call_llm(prompt: str, stage: str = "stage_01") -> str:
    """
    Send a prompt to the configured backend and return the raw response text.

    Args:
        prompt: The full prompt string to send.
        stage:  Stage key (e.g. "stage_01") used to look up the temperature
                in config.TEMPERATURE.

    Returns:
        Raw response string from the model (may contain markdown fences —
        callers are responsible for stripping these before JSON parsing).

    Raises:
        ConnectionError: Ollama is not running or unreachable.
        TimeoutError:    The model did not respond within the timeout.
        RuntimeError:    All retries exhausted.
    """
    temperature = config.TEMPERATURE.get(stage, 0.7)

    for attempt in range(1, config.MAX_RETRIES + 1):
        try:
            if config.BACKEND == "anthropic":
                return _call_anthropic(prompt, temperature)
            else:
                return _call_ollama(prompt, temperature)
        except (json.JSONDecodeError, ValueError) as exc:
            if attempt < config.MAX_RETRIES:
                wait = attempt * 2
                print(f"  ⚠ Attempt {attempt} failed ({exc}), retrying in {wait}s...")
                time.sleep(wait)
            else:
                raise RuntimeError(
                    f"All {config.MAX_RETRIES} attempts failed for stage '{stage}'."
                ) from exc


def _call_ollama(prompt: str, temperature: float) -> str:
    """Send a prompt to a local Ollama instance."""
    import requests

    payload = {
        "model":  config.OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "keep_alive": config.OLLAMA_KEEP_ALIVE,
        "options": {
            "num_ctx":     config.MAX_TOKENS,
            "temperature": temperature,
            "num_predict": -1,
        },
    }

    try:
        response = requests.post(
            config.OLLAMA_BASE_URL,
            json=payload,
            timeout=config.OLLAMA_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response.json().get("response", "").strip()

    except requests.exceptions.ConnectionError:
        raise ConnectionError(
            f"Could not connect to Ollama at {config.OLLAMA_BASE_URL}. "
            "Is Ollama running? Start it with: ollama serve"
        )
    except requests.exceptions.Timeout:
        raise TimeoutError(
            f"Ollama did not respond within {config.OLLAMA_TIMEOUT_SECONDS}s. "
            "Try a smaller model or increase OLLAMA_TIMEOUT_SECONDS in config.py."
        )


def _call_anthropic(prompt: str, temperature: float) -> str:
    """Send a prompt to the Anthropic API."""
    try:
        import anthropic
    except ImportError:
        raise ImportError(
            "The 'anthropic' package is required for the Anthropic backend. "
            "Install it with: pip install anthropic"
        )

    client = anthropic.Anthropic()
    message = client.messages.create(
        model=config.ANTHROPIC_MODEL,
        max_tokens=config.MAX_TOKENS,
        temperature=temperature,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text.strip()


def parse_json_response(raw: str) -> dict | list:
    """
    Strip markdown code fences and parse JSON from a raw LLM response.

    Raises:
        json.JSONDecodeError: If the response is not valid JSON after stripping.
    """
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    return json.loads(cleaned)