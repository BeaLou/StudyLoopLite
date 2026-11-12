"""SQLite: um arquivo único. Cada operação abre a sua própria conexão (seguro com threads)."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    model TEXT NOT NULL,
    input_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    cache_read_tokens INTEGER NOT NULL DEFAULT 0,
    cache_creation_tokens INTEGER NOT NULL DEFAULT 0
);
"""


class Database:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def init(self) -> None:
        """Cria a pasta e as tabelas, se ainda não existirem."""
        if str(self.path) != ":memory:":
            self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as conn:
            conn.executescript(SCHEMA)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def record_usage(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cache_read_tokens: int = 0,
        cache_creation_tokens: int = 0,
    ) -> None:
        """Registra o consumo de tokens de uma chamada (nunca o conteúdo da conversa)."""
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO usage (created_at, model, input_tokens, output_tokens, "
                "cache_read_tokens, cache_creation_tokens) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    datetime.now(UTC).isoformat(),
                    model,
                    input_tokens,
                    output_tokens,
                    cache_read_tokens,
                    cache_creation_tokens,
                ),
            )

    def usage_totals(self) -> dict[str, int]:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS calls, "
                "COALESCE(SUM(input_tokens), 0) AS input_tokens, "
                "COALESCE(SUM(output_tokens), 0) AS output_tokens, "
                "COALESCE(SUM(cache_read_tokens), 0) AS cache_read_tokens, "
                "COALESCE(SUM(cache_creation_tokens), 0) AS cache_creation_tokens "
                "FROM usage"
            ).fetchone()
        return dict(row)
