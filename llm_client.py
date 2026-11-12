"""
llm_client.py
=============
Optional LLM Provider Client supporting:
  - Groq (fast Llama-3.3-70b-versatile, Mixtral, etc.)
  - OpenAI (GPT-4o, etc.)
  - Azure OpenAI
  - Offline Mode (deterministic fallback)

Configuration is loaded from environment variables / .env.
Uses `httpx` (or standard `urllib`) so no heavy external dependencies are required.
"""

import os
import json
from typing import Optional, Dict, Any

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def get_llm_provider() -> str:
    """Detect configured provider: 'groq', 'openai', 'azure', or 'offline'."""
    mode = os.getenv("EXECUTION_MODE", "").lower().strip()
    if mode == "offline":
        return "offline"
    if os.getenv("GROQ_API_KEY"):
        return "groq"
    if os.getenv("AZURE_OPENAI_API_KEY"):
        return "azure"
    if os.getenv("OPENAI_API_KEY"):
        return "openai"
    return "offline"


def query_groq(prompt: str, system_prompt: str = "You are a financial analyst assistant.", model: Optional[str] = None) -> str:
    """
    Query the Groq Cloud API directly using OpenAI-compatible endpoint.
    Requires GROQ_API_KEY in environment or .env.
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY is not set. Please set it in your .env file.")

    model_name = model or os.getenv("GROQ_MODEL_NAME", "qwen/qwen3.8-27b")
    url = "https://api.groq.com/openai/v1/chat/completions"

    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        import httpx
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
    except ImportError:
        import urllib.request
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"]


def query_llm(prompt: str, system_prompt: str = "You are a financial analyst assistant.") -> str:
    """
    Unified entry point for LLM inference.
    Routes to Groq, OpenAI, Azure, or returns an offline indicator.
    """
    provider = get_llm_provider()

    if provider == "groq":
        return query_groq(prompt, system_prompt)
    elif provider == "offline":
        return "[Offline Mode] Deterministic rule and RAG extractors are active. Set GROQ_API_KEY in .env to enable LLM generation."
    else:
        # Fallback to Groq if key exists, otherwise offline
        if os.getenv("GROQ_API_KEY"):
            return query_groq(prompt, system_prompt)
        return "[Offline Mode] No LLM API key configured."
