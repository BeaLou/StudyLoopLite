"""Ingestão incremental por documento: só reindexa o que mudou, em uma transação."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

from studyloop.db import Database
from studyloop.ingest.chunk import chunk_sections
from studyloop.ingest.extract import extract_sections

IngestStatus = Literal["created", "updated", "unchanged"]


@dataclass(frozen=True)
class IngestResult:
    document_id: int
    status: IngestStatus
    chunk_count: int


def ingest_document(
    db: Database,
    *,
    source_id: str,
    name: str,
    mime_type: str,
    modified_time: str | None,
    data: bytes,
) -> IngestResult:
    """Indexa um arquivo. Só o texto extraído é guardado; os bytes originais são descartados.

    Se `modified_time` for igual ao já indexado, nada é refeito. Caso contrário, os trechos
    antigos do documento são trocados pelos novos, sem tocar nos demais documentos.
    """
    with db.connect() as conn:
        row = conn.execute(
            "SELECT id, modified_time FROM documents WHERE source_id = ?", (source_id,)
        ).fetchone()
        if row and modified_time is not None and row["modified_time"] == modified_time:
            count = conn.execute(
                "SELECT COUNT(*) FROM chunks WHERE document_id = ?", (row["id"],)
            ).fetchone()[0]
            return IngestResult(row["id"], "unchanged", count)

    # Extrair fora da transação: falhas aqui não deixam o índice pela metade.
    chunks = chunk_sections(extract_sections(name, mime_type, data))
    now = datetime.now(UTC).isoformat()

    with db.connect() as conn:
        if row:
            document_id = row["id"]
            conn.execute(
                "UPDATE documents SET name = ?, mime_type = ?, modified_time = ?, synced_at = ? "
                "WHERE id = ?",
                (name, mime_type, modified_time, now, document_id),
            )
            conn.execute("DELETE FROM chunks WHERE document_id = ?", (document_id,))
            status: IngestStatus = "updated"
        else:
            cursor = conn.execute(
                "INSERT INTO documents (source_id, name, mime_type, modified_time, synced_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (source_id, name, mime_type, modified_time, now),
            )
            document_id = int(cursor.lastrowid or 0)
            status = "created"
        conn.executemany(
            "INSERT INTO chunks (document_id, position, page, heading, text) "
            "VALUES (?, ?, ?, ?, ?)",
            [(document_id, i, c.page, c.heading, c.text) for i, c in enumerate(chunks)],
        )
    return IngestResult(document_id, status, len(chunks))


def remove_document(db: Database, source_id: str) -> bool:
    """Remove um documento e seus trechos do índice. Devolve se ele existia."""
    with db.connect() as conn:
        row = conn.execute("SELECT id FROM documents WHERE source_id = ?", (source_id,)).fetchone()
        if not row:
            return False
        conn.execute("DELETE FROM chunks WHERE document_id = ?", (row["id"],))
        conn.execute("DELETE FROM documents WHERE id = ?", (row["id"],))
    return True


def list_documents(db: Database) -> list[dict[str, object]]:
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT d.id, d.source_id, d.name, d.mime_type, d.modified_time, d.synced_at, "
            "COUNT(c.id) AS chunk_count FROM documents d "
            "LEFT JOIN chunks c ON c.document_id = d.id "
            "GROUP BY d.id ORDER BY d.name"
        ).fetchall()
    return [dict(r) for r in rows]
