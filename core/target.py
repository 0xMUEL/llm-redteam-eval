"""
Target model interface.
Wraps Ollama (or OpenAI-compatible) API for the model being evaluated.
"""

import requests
import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ModelResponse:
    """Structured response from a model call."""
    content: str
    model: str
    latency_ms: float
    token_count: int = 0
    raw: dict = field(default_factory=dict)


class TargetModel:
    """Interface to the target LLM being evaluated."""

    def __init__(self, config: dict):
        self.provider = config.get("provider", "ollama")
        self.model = config["model"]
        self.base_url = config.get("base_url", "http://localhost:11434")
        self.temperature = config.get("temperature", 0.7)
        self.max_tokens = config.get("max_tokens", 1024)

    def chat(
        self,
        messages: list[dict],
        system_prompt: Optional[str] = None,
    ) -> ModelResponse:
        """
        Send a conversation to the target model.

        Args:
            messages: List of {"role": "user"|"assistant", "content": "..."}
            system_prompt: Optional system-level instruction.

        Returns:
            ModelResponse with the model's reply.
        """
        if self.provider == "ollama":
            return self._call_ollama(messages, system_prompt)
        elif self.provider == "openai_compatible":
            return self._call_openai_compatible(messages, system_prompt)
        else:
            raise ValueError(f"Unknown provider: {self.provider}")

    def _call_ollama(
        self, messages: list[dict], system_prompt: Optional[str]
    ) -> ModelResponse:
        """Call Ollama's /api/chat endpoint."""
        payload_messages = []
        if system_prompt:
            payload_messages.append({"role": "system", "content": system_prompt})
        payload_messages.extend(messages)

        payload = {
            "model": self.model,
            "messages": payload_messages,
            "stream": False,
            "options": {
                "temperature": self.temperature,
                "num_predict": self.max_tokens,
            },
        }

        t0 = time.perf_counter()
        try:
            resp = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=120,
            )
            resp.raise_for_status()
        except requests.RequestException as e:
            return ModelResponse(
                content=f"[ERROR] Model call failed: {e}",
                model=self.model,
                latency_ms=(time.perf_counter() - t0) * 1000,
            )

        latency = (time.perf_counter() - t0) * 1000
        data = resp.json()

        return ModelResponse(
            content=data.get("message", {}).get("content", ""),
            model=self.model,
            latency_ms=latency,
            token_count=data.get("eval_count", 0),
            raw=data,
        )

    def _call_openai_compatible(
        self, messages: list[dict], system_prompt: Optional[str]
    ) -> ModelResponse:
        """Call any OpenAI-compatible API (vLLM, LM Studio, etc.)."""
        payload_messages = []
        if system_prompt:
            payload_messages.append({"role": "system", "content": system_prompt})
        payload_messages.extend(messages)

        payload = {
            "model": self.model,
            "messages": payload_messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

        t0 = time.perf_counter()
        try:
            resp = requests.post(
                f"{self.base_url}/v1/chat/completions",
                json=payload,
                timeout=120,
            )
            resp.raise_for_status()
        except requests.RequestException as e:
            return ModelResponse(
                content=f"[ERROR] Model call failed: {e}",
                model=self.model,
                latency_ms=(time.perf_counter() - t0) * 1000,
            )

        latency = (time.perf_counter() - t0) * 1000
        data = resp.json()
        choice = data.get("choices", [{}])[0]

        return ModelResponse(
            content=choice.get("message", {}).get("content", ""),
            model=self.model,
            latency_ms=latency,
            token_count=data.get("usage", {}).get("completion_tokens", 0),
            raw=data,
        )


class AttackerModel(TargetModel):
    """
    The attacker LLM that generates adversarial prompts.
    Same interface as TargetModel, separate config.
    """
    pass
