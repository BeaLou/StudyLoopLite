"""Interface que o resto do app usa para falar com qualquer LLM."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Protocol, TypedDict

ModelTier = Literal["cheap", "smart"]


class Message(TypedDict):
    role: Literal["user", "assistant"]
    content: str


@dataclass(frozen=True)
class Usage:
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0


class LLMProvider(Protocol):
    def chat(self, system: str, messages: list[Message], *, model_tier: ModelTier) -> str:
        """Resposta em texto."""
        ...

    def structured(
        self,
        system: str,
        messages: list[Message],
        schema: dict[str, Any],
        *,
        model_tier: ModelTier,
    ) -> dict[str, Any]:
        """Resposta em JSON que obedece ao `schema` (usada por quizzes e mapas, a partir do M3)."""
        ...
