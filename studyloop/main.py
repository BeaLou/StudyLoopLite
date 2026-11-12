"""Aplicação FastAPI. Rode com: uvicorn studyloop.main:app --reload"""

# Sem `from __future__ import annotations` de propósito: o FastAPI precisa resolver as
# anotações das rotas (inclusive `get_provider`, que é local a `create_app`).
from dataclasses import asdict
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from pydantic import BaseModel, Field

from studyloop import __version__
from studyloop.config import Settings, load_dotenv, load_settings
from studyloop.db import Database
from studyloop.ingest.service import list_documents
from studyloop.llm.base import LLMProvider, Message
from studyloop.llm.claude import ClaudeProvider, create_claude_client
from studyloop.rag.search import DEFAULT_TOP_K, search

MENTOR_SYSTEM_PROMPT = (
    "Você é o mentor de estudos do StudyLoop Lite. Responda sempre em português do Brasil, "
    "de forma clara e objetiva, e ajude a pessoa a aprender. "
    "(Nesta versão você ainda não lê os materiais do usuário.)"
)


class HistoryItem(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    history: list[HistoryItem] = Field(default_factory=list)


class ChatResponse(BaseModel):
    reply: str


class SearchHitResponse(BaseModel):
    chunk_id: int
    document_id: int
    document_name: str
    page: int | None
    heading: str | None
    text: str
    score: float


def create_app(settings: Settings | None = None, provider: LLMProvider | None = None) -> FastAPI:
    """Monta o app. Nos testes, passe `settings` e um `provider` falso."""
    if settings is None:
        load_dotenv()
        settings = load_settings()

    database = Database(settings.db_path)
    database.init()

    if provider is None and settings.anthropic_api_key:
        provider = ClaudeProvider(
            create_claude_client(settings.anthropic_api_key),
            settings.models,
            max_tokens=settings.max_tokens,
            on_usage=lambda u: database.record_usage(
                u.model,
                u.input_tokens,
                u.output_tokens,
                u.cache_read_tokens,
                u.cache_creation_tokens,
            ),
        )

    app = FastAPI(title="StudyLoop Lite", version=__version__)
    app.state.settings = settings
    app.state.database = database
    app.state.provider = provider

    def get_provider(request: Request) -> LLMProvider:
        current = request.app.state.provider
        if current is None:
            raise HTTPException(
                status_code=503,
                detail="ANTHROPIC_API_KEY não configurada. Preencha o .env e reinicie o servidor.",
            )
        return current

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    @app.post("/chat", response_model=ChatResponse)
    def chat(
        body: ChatRequest, llm: Annotated[LLMProvider, Depends(get_provider)]
    ) -> ChatResponse:
        messages: list[Message] = [{"role": h.role, "content": h.content} for h in body.history]
        messages.append({"role": "user", "content": body.message})
        reply = llm.chat(MENTOR_SYSTEM_PROMPT, messages, model_tier="smart")
        return ChatResponse(reply=reply)

    @app.get("/documents")
    def documents() -> list[dict[str, object]]:
        return list_documents(database)

    @app.get("/search", response_model=list[SearchHitResponse])
    def search_endpoint(
        q: str, k: int = Query(DEFAULT_TOP_K, ge=1, le=20)
    ) -> list[SearchHitResponse]:
        hits = search(database, q, k=k)
        return [SearchHitResponse(**asdict(h)) for h in hits]

    return app


_default_app: FastAPI | None = None


def __getattr__(name: str) -> FastAPI:
    """Cria o `app` só quando o uvicorn pede, para o import não ter efeitos colaterais."""
    global _default_app
    if name == "app":
        if _default_app is None:
            _default_app = create_app()
        return _default_app
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
