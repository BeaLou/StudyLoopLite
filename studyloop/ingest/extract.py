"""Extração de texto. Recebe os bytes do arquivo e devolve seções; nada é gravado em disco."""

from __future__ import annotations

import io
import re
from dataclasses import dataclass
from pathlib import PurePath

GOOGLE_DOC = "application/vnd.google-apps.document"
GOOGLE_SHEET = "application/vnd.google-apps.spreadsheet"
PDF = "application/pdf"
DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

_TEXT_EXTENSIONS = {".txt", ".md", ".markdown", ".csv"}
_MD_HEADING = re.compile(r"^\s{0,3}#{1,6}\s+(.*\S)\s*$")


class UnsupportedFileType(ValueError):
    """O tipo do arquivo não é suportado."""


class EmptyDocument(ValueError):
    """Nenhum texto foi extraído (ex.: PDF escaneado, que precisaria de OCR)."""


@dataclass(frozen=True)
class Section:
    """Um bloco contínuo de texto, com a página e o título de onde veio."""

    text: str
    page: int | None = None
    heading: str | None = None


def extract_sections(name: str, mime_type: str, data: bytes) -> list[Section]:
    """Extrai o texto de um arquivo. Google Docs/Sheets chegam já exportados como texto."""
    kind = _detect_kind(name, mime_type)
    if kind == "pdf":
        sections = _from_pdf(data)
    elif kind == "docx":
        sections = _from_docx(data)
    else:
        sections = _from_text(_decode(data), markdown=kind == "markdown")
    sections = [s for s in sections if s.text.strip()]
    if not sections:
        raise EmptyDocument(f"Nenhum texto encontrado em {name!r}.")
    return sections


def _detect_kind(name: str, mime_type: str) -> str:
    ext = PurePath(name).suffix.lower()
    if mime_type == PDF or ext == ".pdf":
        return "pdf"
    if mime_type == DOCX or ext == ".docx":
        return "docx"
    if ext in {".md", ".markdown"}:
        return "markdown"
    if mime_type in {GOOGLE_DOC, GOOGLE_SHEET} or mime_type.startswith("text/"):
        return "text"
    if ext in _TEXT_EXTENSIONS:
        return "text"
    raise UnsupportedFileType(
        f"Tipo de arquivo não suportado: {name!r} ({mime_type or 'sem mime'})"
    )


def _decode(data: bytes) -> str:
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data.decode("latin-1")


def _from_text(text: str, *, markdown: bool) -> list[Section]:
    if not markdown:
        return [Section(text=text)]
    sections: list[Section] = []
    heading: str | None = None
    buffer: list[str] = []

    def flush() -> None:
        body = "\n".join(buffer).strip()
        if body:
            sections.append(Section(text=body, heading=heading))
        buffer.clear()

    for line in text.splitlines():
        match = _MD_HEADING.match(line)
        if match:
            flush()
            heading = match.group(1)
        else:
            buffer.append(line)
    flush()
    return sections


def _from_pdf(data: bytes) -> list[Section]:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    return [
        Section(text=page.extract_text() or "", page=number)
        for number, page in enumerate(reader.pages, start=1)
    ]


def _from_docx(data: bytes) -> list[Section]:
    from docx import Document

    document = Document(io.BytesIO(data))
    sections: list[Section] = []
    heading: str | None = None
    buffer: list[str] = []

    def flush() -> None:
        body = "\n\n".join(buffer).strip()
        if body:
            sections.append(Section(text=body, heading=heading))
        buffer.clear()

    for paragraph in document.paragraphs:
        text = paragraph.text.strip()
        if not text:
            continue
        style = (paragraph.style.name or "") if paragraph.style is not None else ""
        if style.lower().startswith(("heading", "título", "title")):
            flush()
            heading = text
        else:
            buffer.append(text)
    flush()
    return sections
