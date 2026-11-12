"""Divisão do texto em trechos (chunks) de tamanho parecido, com pequena sobreposição."""

from __future__ import annotations

import re
from dataclasses import dataclass

from studyloop.ingest.extract import Section

# Medido em palavras (aprox. 1,5 token por palavra em português): 400 palavras ~ 600 tokens.
TARGET_WORDS = 400
MAX_WORDS = 550
OVERLAP_WORDS = 40

_PARAGRAPH_SPLIT = re.compile(r"\n\s*\n")
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


@dataclass(frozen=True)
class Chunk:
    text: str
    page: int | None = None
    heading: str | None = None


def chunk_sections(
    sections: list[Section],
    *,
    target_words: int = TARGET_WORDS,
    max_words: int = MAX_WORDS,
    overlap_words: int = OVERLAP_WORDS,
) -> list[Chunk]:
    """Cria os trechos. Nenhum atravessa páginas ou títulos, para a citação ser exata."""
    chunks: list[Chunk] = []
    for section in sections:
        for text in _chunk_text(section.text, target_words, max_words, overlap_words):
            chunks.append(Chunk(text=text, page=section.page, heading=section.heading))
    return chunks


def _chunk_text(text: str, target: int, maximum: int, overlap: int) -> list[str]:
    pieces: list[str] = []
    for paragraph in _PARAGRAPH_SPLIT.split(text):
        paragraph = paragraph.strip()
        if paragraph:
            pieces.extend(_split_long(paragraph, maximum))

    chunks: list[str] = []
    current: list[str] = []
    count = 0
    added = 0  # parágrafos novos no trecho atual (a cauda repetida não conta)
    for piece in pieces:
        words = len(piece.split())
        if added and (count + words > maximum or count >= target):
            chunks.append("\n\n".join(current))
            tail = _tail(chunks[-1], overlap)
            current = [tail] if tail else []
            count = len(tail.split())
            added = 0
        current.append(piece)
        count += words
        added += 1
    if added:
        chunks.append("\n\n".join(current))
    return chunks


def _split_long(paragraph: str, maximum: int) -> list[str]:
    """Quebra parágrafos maiores que `maximum` por frases e, em último caso, por palavras."""
    if len(paragraph.split()) <= maximum:
        return [paragraph]
    parts: list[str] = []
    buffer: list[str] = []
    count = 0
    for sentence in _SENTENCE_SPLIT.split(paragraph):
        words = sentence.split()
        if len(words) > maximum:
            if buffer:
                parts.append(" ".join(buffer))
                buffer, count = [], 0
            parts.extend(
                " ".join(words[i : i + maximum]) for i in range(0, len(words), maximum)
            )
            continue
        if count + len(words) > maximum and buffer:
            parts.append(" ".join(buffer))
            buffer, count = [], 0
        buffer.append(sentence)
        count += len(words)
    if buffer:
        parts.append(" ".join(buffer))
    return parts


def _tail(text: str, words: int) -> str:
    return " ".join(text.split()[-words:]) if words else ""
