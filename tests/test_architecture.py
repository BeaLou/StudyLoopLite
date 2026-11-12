"""Regras do CLAUDE.md que podem ser verificadas automaticamente."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACKAGE = ROOT / "studyloop"
IMPORT_ANTHROPIC = re.compile(r"^\s*(import anthropic|from anthropic)\b", re.MULTILINE)


def test_so_o_modulo_llm_importa_anthropic():
    for path in PACKAGE.rglob("*.py"):
        if "llm" in path.relative_to(PACKAGE).parts:
            continue
        assert not IMPORT_ANTHROPIC.search(path.read_text(encoding="utf-8")), (
            f"{path.relative_to(ROOT)} importa anthropic fora de studyloop/llm/"
        )


def test_ids_de_modelo_ficam_so_na_configuracao():
    modelo = re.compile(r"claude-(haiku|sonnet|opus|fable|mythos)-[\w.-]+")
    for path in PACKAGE.rglob("*.py"):
        if path.name == "config.py":
            continue
        assert not modelo.search(path.read_text(encoding="utf-8")), (
            f"{path.relative_to(ROOT)} tem ID de modelo fixo no código"
        )
