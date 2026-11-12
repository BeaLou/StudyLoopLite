"""Ferramenta de desenvolvimento: indexa arquivos locais para testar a busca antes do Drive (M1b).

    python -m studyloop.ingest.cli material.pdf notas.md
    python -m studyloop.ingest.cli --buscar "modelagem plana"
"""

from __future__ import annotations

import argparse
import mimetypes
from datetime import UTC, datetime
from pathlib import Path

from studyloop.config import load_dotenv, load_settings
from studyloop.db import Database
from studyloop.ingest.extract import EmptyDocument, UnsupportedFileType
from studyloop.ingest.service import ingest_document
from studyloop.rag.search import search


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("arquivos", nargs="*", type=Path)
    parser.add_argument("--buscar", metavar="CONSULTA", help="busca nos documentos já indexados")
    args = parser.parse_args(argv)

    load_dotenv()
    db = Database(load_settings().db_path)
    db.init()

    for path in args.arquivos:
        path = path.resolve()
        mtime = datetime.fromtimestamp(path.stat().st_mtime, UTC).isoformat()
        try:
            result = ingest_document(
                db,
                source_id=f"local:{path}",
                name=path.name,
                mime_type=mimetypes.guess_type(path.name)[0] or "",
                modified_time=mtime,
                data=path.read_bytes(),
            )
        except (UnsupportedFileType, EmptyDocument) as error:
            print(f"- {path.name}: ignorado ({error})")
            continue
        print(f"- {path.name}: {result.status}, {result.chunk_count} trechos")

    if args.buscar:
        for hit in search(db, args.buscar):
            local = f", p. {hit.page}" if hit.page else ""
            titulo = f" — {hit.heading}" if hit.heading else ""
            print(f"\n[{hit.document_name}{local}{titulo}] (relevância {hit.score:.2f})")
            print(hit.text[:300].replace("\n", " "))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
