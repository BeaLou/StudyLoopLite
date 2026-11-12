import pytest
from helpers import make_docx, make_pdf

from studyloop.ingest.extract import (
    GOOGLE_DOC,
    EmptyDocument,
    UnsupportedFileType,
    extract_sections,
)


def test_texto_simples_utf8():
    secoes = extract_sections("notas.txt", "text/plain", "Corte enviesado é útil.".encode())
    assert [s.text for s in secoes] == ["Corte enviesado é útil."]


def test_texto_latin1_cai_no_fallback():
    secoes = extract_sections("velho.txt", "", "Costura à mão".encode("latin-1"))
    assert secoes[0].text == "Costura à mão"


def test_bom_utf8_e_removido():
    secoes = extract_sections("bom.txt", "text/plain", b"\xef\xbb\xbfTexto")
    assert secoes[0].text == "Texto"


def test_markdown_separa_por_titulos():
    md = "# Moulage\nTécnica 3D.\n\n## Passos\nPrender o tecido.\n\n# Croqui\nDesenho rápido.\n"
    secoes = extract_sections("aula.md", "text/markdown", md.encode())
    assert [(s.heading, s.text) for s in secoes] == [
        ("Moulage", "Técnica 3D."),
        ("Passos", "Prender o tecido."),
        ("Croqui", "Desenho rápido."),
    ]


def test_markdown_sem_titulo_mantem_o_texto_inicial():
    secoes = extract_sections("x.md", "", b"Introducao solta\n\n# Depois\ncorpo")
    assert [(s.heading, s.text) for s in secoes] == [
        (None, "Introducao solta"),
        ("Depois", "corpo"),
    ]


def test_google_doc_exportado_como_texto():
    secoes = extract_sections("Minha aula", GOOGLE_DOC, "Conteúdo exportado".encode())
    assert secoes[0].text == "Conteúdo exportado"


def test_pdf_devolve_uma_secao_por_pagina_com_numero():
    pdf = make_pdf(["Primeira página: moulage", "Segunda página: ação"])
    secoes = extract_sections("apostila.pdf", "application/pdf", pdf)
    assert [(s.page, s.text) for s in secoes] == [
        (1, "Primeira página: moulage"),
        (2, "Segunda página: ação"),
    ]


def test_pdf_pelo_nome_mesmo_sem_mime():
    secoes = extract_sections("apostila.pdf", "", make_pdf(["Olá"]))
    assert secoes[0].page == 1


def test_pdf_sem_texto_levanta_empty_document():
    with pytest.raises(EmptyDocument):
        extract_sections("escaneado.pdf", "application/pdf", make_pdf([""]))


def test_docx_usa_titulos_como_contexto():
    docx = make_docx(
        [("h", "Patternmaking"), ("p", "Base do corpete."), ("h", "Spec sheet"), ("p", "Medidas.")]
    )
    secoes = extract_sections("aula.docx", "", docx)
    assert [(s.heading, s.text) for s in secoes] == [
        ("Patternmaking", "Base do corpete."),
        ("Spec sheet", "Medidas."),
    ]


def test_tipo_nao_suportado():
    with pytest.raises(UnsupportedFileType):
        extract_sections("programa.exe", "application/octet-stream", b"MZ")


def test_texto_vazio_levanta_empty_document():
    with pytest.raises(EmptyDocument):
        extract_sections("vazio.txt", "text/plain", b"   \n\n")
