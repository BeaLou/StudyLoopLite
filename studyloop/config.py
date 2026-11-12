"""Configuração lida de variáveis de ambiente (e de um .env opcional)."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

DEFAULT_DB_PATH = "data/studyloop.db"
DEFAULT_MODEL_CHEAP = "claude-haiku-5-5"
DEFAULT_MODEL_SMART = "claude-sonnet-5-5"
DEFAULT_MAX_TOKENS = 1024


@dataclass(frozen=True)
class Settings:
    """Configurações do app. A chave da API nunca é exibida no repr."""

    anthropic_api_key: str | None
    db_path: Path
    model_cheap: str
    model_smart: str
    max_tokens: int

    def __repr__(self) -> str:
        has_key = "sim" if self.anthropic_api_key else "não"
        return (
            f"Settings(chave_api={has_key}, db_path={self.db_path}, "
            f"model_cheap={self.model_cheap}, model_smart={self.model_smart}, "
            f"max_tokens={self.max_tokens})"
        )

    @property
    def models(self) -> dict[str, str]:
        """Mapeia o nível (`cheap`/`smart`) para o ID do modelo."""
        return {"cheap": self.model_cheap, "smart": self.model_smart}


def load_dotenv(path: str | Path = ".env", environ: dict[str, str] | None = None) -> None:
    """Carrega pares CHAVE=valor de um .env sem sobrescrever variáveis já definidas."""
    target = os.environ if environ is None else environ
    file = Path(path)
    if not file.is_file():
        return
    for raw in file.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip("'\"")
        if key and key not in target:
            target[key] = value


def load_settings(env: Mapping[str, str] | None = None) -> Settings:
    """Monta as configurações a partir do ambiente (ou de um mapa passado nos testes)."""
    source = os.environ if env is None else env
    api_key = (source.get("ANTHROPIC_API_KEY") or "").strip() or None
    return Settings(
        anthropic_api_key=api_key,
        db_path=Path(source.get("STUDYLOOP_DB_PATH") or DEFAULT_DB_PATH),
        model_cheap=source.get("STUDYLOOP_MODEL_CHEAP") or DEFAULT_MODEL_CHEAP,
        model_smart=source.get("STUDYLOOP_MODEL_SMART") or DEFAULT_MODEL_SMART,
        max_tokens=int(source.get("STUDYLOOP_MAX_TOKENS") or DEFAULT_MAX_TOKENS),
    )
