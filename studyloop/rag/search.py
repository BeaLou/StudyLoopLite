"""Busca por palavra-chave (SQLite FTS5, ranking BM25), sem acentos."""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

from studyloop.db import Database

DEFAULT_TOP_K = 6

_WORD = re.compile(r"\w+", re.UNICODE)
# Palavras muito comuns em português: pouco ajudam a achar o trecho certo.
_STOPWORDS = frozenset(
    "a o as os um uma uns umas de do da dos das em no na nos nas por para com sem sobre "
    "e ou que se ao aos à às é são foi ser como mais mas já não eu me meu minha seu sua "
    "qual quais quando onde quem isso isto este esta esse essa ele ela eles elas".split()
)
_MIN_STEM_LEN = 6  # palavras com 6+ letras viram prefixo (modelagens -> modelage*)


@dataclass(frozen=True)
class SearchHit:
    chunk_id: int
    document_id: int
    document_name: str
    page: int | None
    heading: str | None
    text: str
    score: float  # maior = mais relevante


def build_match_query(query: str) -> str | None:
    """Converte texto livre em uma consulta FTS5 segura (termos com OR, prefixo leve).

    Devolve None se não sobrar nenhum termo útil. Nunca repassa a sintaxe do FTS5 ao usuário,
    então aspas, parênteses e operadores digitados viram texto comum.
    """
    terms: list[str] = []
    for word in _WORD.findall(query.lower()):
        if len(word) < 2 or word in _STOPWORDS or word in terms:
            continue
        terms.append(word)
    if not terms:
        return None
    parts = []
    for word in terms:
        if len(word) >= _MIN_STEM_LEN:
            parts.append(f'"{word[:-2]}"*')
        else:
            parts.append(f'"{word}"')
    return " OR ".join(parts)


def search(
    db: Database,
    query: str,
    *,
    k: int = DEFAULT_TOP_K,
    document_ids: Sequence[int] | None = None,
) -> list[SearchHit]:
    """Devolve os `k` trechos mais relevantes, opcionalmente restritos a certos documentos."""
    match = build_match_query(query)
    if match is None or k <= 0:
        return []
    sql = (
        "SELECT c.id, c.document_id, d.name, c.page, c.heading, c.text, "
        "bm25(chunks_fts, 1.0, 2.0) AS rank "
        "FROM chunks_fts JOIN chunks c ON c.id = chunks_fts.rowid "
        "JOIN documents d ON d.id = c.document_id "
        "WHERE chunks_fts MATCH ?"
    )
    params: list[object] = [match]
    if document_ids is not None:
        if not document_ids:
            return []
        sql += f" AND c.document_id IN ({','.join('?' * len(document_ids))})"
        params.extend(document_ids)
    sql += " ORDER BY rank LIMIT ?"
    params.append(k)
    with db.connect() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [
        SearchHit(
            chunk_id=r["id"],
            document_id=r["document_id"],
            document_name=r["name"],
            page=r["page"],
            heading=r["heading"],
            text=r["text"],
            score=-float(r["rank"]),
        )
        for r in rows
    ]
