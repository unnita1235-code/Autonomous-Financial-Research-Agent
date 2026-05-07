"""
agents/llm_client.py
────────────────────
A thin, provider-agnostic LLM client that wraps OpenAI and Anthropic chat
completion APIs behind a single `.chat()` interface.

Provider is selected via the LLM_PROVIDER env var:
    "openai"    → uses openai.OpenAI (requires OPENAI_API_KEY)
    "anthropic" → uses anthropic.Anthropic (requires ANTHROPIC_API_KEY)

Design decisions:
  • No streaming — the ReAct loop needs the full JSON blob before parsing.
  • No function-calling / tool_use — we handle dispatch ourselves.
  • response_format=json_object enforced for OpenAI to guarantee valid JSON.
  • For Anthropic we rely on the system prompt constraint + retry logic in
    the loop layer (Claude respects JSON-only instructions reliably).
"""

import os
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class LLMClient:
    """
    Minimal LLM abstraction.  Supports OpenAI and Anthropic via env-var
    based selection.

    Usage:
        client = LLMClient()
        reply = client.chat(messages=[
            {"role": "system", "content": "..."},
            {"role": "user",   "content": "..."},
        ])
    """

    def __init__(
        self,
        provider: str | None = None,
        model: str | None = None,
    ):
        """
        Args:
            provider: "openai" or "anthropic".  Falls back to env LLM_PROVIDER,
                      then defaults to "openai".
            model:    Model name override.  Defaults to gpt-4o / claude-sonnet-4-20250514.
        """
        self.provider = (provider or os.getenv("LLM_PROVIDER", "openai")).lower()

        if self.provider == "openai":
            self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o")
            self._init_openai()
        elif self.provider == "anthropic":
            self.model = model or os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
            self._init_anthropic()
        elif self.provider == "gemini":
            self.model = model or os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
            self._init_gemini()
        elif self.provider == "groq":
            self.model = model or os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
            self._init_groq()
        else:
            raise ValueError(
                f"Unsupported LLM_PROVIDER '{self.provider}'. "
                "Must be 'openai', 'anthropic', 'gemini', or 'groq'."
            )

        logger.info("LLMClient initialised — provider=%s  model=%s", self.provider, self.model)

    # ── Provider-specific init ──────────────────────────────────────────
    def _init_openai(self) -> None:
        try:
            from openai import OpenAI  # type: ignore
        except ImportError:
            raise ImportError("pip install openai  — required when LLM_PROVIDER=openai")

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise EnvironmentError("OPENAI_API_KEY env var is not set.")
        self._client = OpenAI(api_key=api_key)

    def _init_anthropic(self) -> None:
        try:
            from anthropic import Anthropic  # type: ignore
        except ImportError:
            raise ImportError("pip install anthropic  — required when LLM_PROVIDER=anthropic")

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise EnvironmentError("ANTHROPIC_API_KEY env var is not set.")
        self._client = Anthropic(api_key=api_key)

    def _init_gemini(self) -> None:
        try:
            import google.generativeai as genai  # type: ignore
        except ImportError:
            raise ImportError("pip install google-generativeai  — required when LLM_PROVIDER=gemini")

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise EnvironmentError("GEMINI_API_KEY env var is not set.")
        genai.configure(api_key=api_key)
        self._client = genai.GenerativeModel(self.model)

    def _init_groq(self) -> None:
        try:
            from groq import Groq  # type: ignore
        except ImportError:
            raise ImportError("pip install groq  — required when LLM_PROVIDER=groq")

        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise EnvironmentError("GROQ_API_KEY env var is not set.")
        self._client = Groq(api_key=api_key)

    # ── Public API ──────────────────────────────────────────────────────
    def chat(
        self,
        messages: List[Dict[str, Any]],
        response_format: str = "json_object",
    ) -> str:
        """
        Send a list of messages and return the assistant's text reply.
        Includes exponential backoff for rate limits.
        """
        import time
        import random

        max_retries = 3
        backoff_base = 2
        
        for attempt in range(max_retries + 1):
            try:
                if self.provider in ("openai", "groq"):
                    return self._chat_openai(messages, response_format)
                elif self.provider == "anthropic":
                    return self._chat_anthropic(messages, response_format)
                else:
                    return self._chat_gemini(messages, response_format)
            except Exception as e:
                error_str = str(e).lower()
                is_rate_limit = "rate limit" in error_str or "429" in error_str
                
                if is_rate_limit and attempt < max_retries:
                    # Exponential backoff with jitter
                    wait_time = (backoff_base ** attempt) + random.uniform(0, 1)
                    # If it's Groq, they often tell us how long to wait
                    if "retry after" in error_str or "try again in" in error_str:
                        try:
                            # Attempt to extract wait time if provided in message
                            import re
                            match = re.search(r"try again in ([\d\.]+)s", error_str)
                            if match:
                                wait_time = float(match.group(1)) + 1.0
                        except:
                            pass
                    
                    logger.warning(
                        "Rate limit hit (%s). Retrying in %.2fs (attempt %d/%d)...",
                        self.provider, wait_time, attempt + 1, max_retries
                    )
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error("LLM call failed after %d retries: %s", attempt, e)
                    raise e

    # ── OpenAI implementation ───────────────────────────────────────────
    def _chat_openai(
        self,
        messages: List[Dict[str, Any]],
        response_format: str = "json_object",
    ) -> str:
        kwargs: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": 1024,
        }
        # Only set response_format for JSON mode; text mode uses default
        if response_format == "json_object":
            kwargs["response_format"] = {"type": "json_object"}

        response = self._client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content
        logger.debug("OpenAI raw response: %s", content[:200])
        return content

    # ── Anthropic implementation ────────────────────────────────────────
    def _chat_anthropic(
        self,
        messages: List[Dict[str, Any]],
        response_format: str = "json_object",
    ) -> str:
        # Anthropic separates the system prompt from messages.
        # response_format is accepted for API compatibility but Anthropic
        # always returns text — JSON enforcement is via system prompt.
        system_text = ""
        chat_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_text += msg["content"] + "\n"
            else:
                chat_messages.append({"role": msg["role"], "content": msg["content"]})

        # Anthropic requires at least one user message
        if not chat_messages:
            chat_messages = [{"role": "user", "content": "Begin."}]

        response = self._client.messages.create(
            model=self.model,
            system=system_text.strip(),
            messages=chat_messages,
            max_tokens=1024,
            temperature=0.2,
        )
        content = response.content[0].text
        logger.debug("Anthropic raw response: %s", content[:200])
        return content

    # ── Gemini implementation ───────────────────────────────────────────
    def _chat_gemini(
        self,
        messages: List[Dict[str, Any]],
        response_format: str = "json_object",
    ) -> str:
        system_text = ""
        chat_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_text += msg["content"] + "\n"
            else:
                role = "model" if msg["role"] == "assistant" else "user"
                chat_messages.append({"role": role, "parts": [msg["content"]]})

        generation_config = {"temperature": 0.2, "max_output_tokens": 1024}
        if response_format == "json_object":
            generation_config["response_mime_type"] = "application/json"

        model = self._client
        if system_text:
            import google.generativeai as genai
            model = genai.GenerativeModel(
                model_name=self.model,
                system_instruction=system_text.strip()
            )

        response = model.generate_content(
            chat_messages,
            generation_config=generation_config
        )
        content = response.text
        logger.debug("Gemini raw response: %s", content[:200])
        return content
