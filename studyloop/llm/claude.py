"""Implementação do LLMProvider com a API da Claude. Único módulo que importa `anthropic`."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from studyloop.llm.base import Message, ModelTier, Usage

UsageCallback = Callable[[Usage], None]


class ClaudeProvider:
    def __init__(
        self,
        client: Any,
        models: dict[str, str],
        *,
        max_tokens: int = 1024,
        on_usage: UsageCallback | None = None,
    ) -> None:
        self._client = client
        self._models = models
        self._max_tokens = max_tokens
        self._on_usage = on_usage

    def _model_for(self, tier: str) -> str:
        try:
            return self._models[tier]
        except KeyError:
            raise ValueError(f"Nível de modelo desconhecido: {tier!r}") from None

    def chat(self, system: str, messages: list[Message], *, model_tier: ModelTier) -> str:
        model = self._model_for(model_tier)
        response = self._client.messages.create(
            model=model,
            max_tokens=self._max_tokens,
            # Bloco de sistema marcado para cache (vale só acima do tamanho mínimo do modelo).
            system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            messages=list(messages),
        )
        self._report_usage(model, getattr(response, "usage", None))
        return "".join(
            block.text for block in response.content if getattr(block, "type", None) == "text"
        )

    def structured(
        self,
        system: str,
        messages: list[Message],
        schema: dict[str, Any],
        *,
        model_tier: ModelTier,
    ) -> dict[str, Any]:
        raise NotImplementedError("Respostas estruturadas entram no M3 (quizzes e mapas).")

    def _report_usage(self, model: str, usage: Any) -> None:
        if self._on_usage is None or usage is None:
            return
        self._on_usage(
            Usage(
                model=model,
                input_tokens=getattr(usage, "input_tokens", 0) or 0,
                output_tokens=getattr(usage, "output_tokens", 0) or 0,
                cache_read_tokens=getattr(usage, "cache_read_input_tokens", 0) or 0,
                cache_creation_tokens=getattr(usage, "cache_creation_input_tokens", 0) or 0,
            )
        )


def create_claude_client(api_key: str) -> Any:
    """Cria o cliente oficial. A importação é tardia para os testes não precisarem do SDK."""
    import anthropic

    return anthropic.Anthropic(api_key=api_key)
