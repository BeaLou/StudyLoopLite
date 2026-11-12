import pytest

from studyloop.db import Database
from studyloop.ingest.service import ingest_document
from studyloop.rag.search import build_match_query, search


@pytest.fixture
def db(tmp_path):
    database = Database(tmp_path / "app.db")
    database.init()
    return database


def indexar(db, source_id, name, text):
    return ingest_document(
        db,
        source_id=source_id,
        name=name,
        mime_type="text/plain",
        modified_time="2026-01-01T00:00:00Z",
        data=text.encode(),
    )


def test_consulta_remove_palavras_comuns():
    assert build_match_query("o que é a barra") == '"barra"'


def test_consulta_so_com_palavras_comuns_vira_none():
    assert build_match_query("o que é a de") is None
    assert build_match_query("   ") is None
    assert build_match_query("!!! ???") is None


def test_consulta_usa_prefixo_em_palavras_longas():
    assert build_match_query("modelagens") == '"modelage"*'
    assert build_match_query("saia") == '"saia"'


def test_consulta_nao_repete_termos_e_une_com_or():
    assert build_match_query("saia saia barra") == '"saia" OR "barra"'


def test_sintaxe_do_fts_digitada_pelo_usuario_nao_quebra(db):
    indexar(db, "a", "a.txt", "Moulage e pences na saia.")
    for consulta in ['moulage AND (', '"aberta', "NEAR(a b)", "col:valor", "saia*", "- + ^ ~"]:
        search(db, consulta)  # não pode levantar exceção


def test_acha_o_documento_certo_e_ordena_por_relevancia(db):
    indexar(db, "a", "moulage.txt", "Moulage é a técnica de modelar o tecido direto no manequim.")
    indexar(db, "b", "croqui.txt", "O croqui é um desenho rápido da silhueta da roupa.")
    indexar(db, "c", "mistura.txt", "Falamos de moulage e de croqui, de moulage e manequim, muito.")

    hits = search(db, "moulage manequim")

    assert hits[0].document_name in {"moulage.txt", "mistura.txt"}
    assert "croqui.txt" not in [h.document_name for h in hits]
    assert hits == sorted(hits, key=lambda h: h.score, reverse=True)


def test_ignora_acentos_e_caixa(db):
    indexar(db, "a", "a.txt", "A Modelagem plana usa moldes de papel.")
    assert search(db, "MODELAGÉM")
    assert search(db, "papél")


def test_prefixo_acha_plural(db):
    indexar(db, "a", "a.txt", "A modelagem plana usa moldes.")
    assert [h.document_name for h in search(db, "modelagens")] == ["a.txt"]


def test_titulo_pesa_mais_que_o_corpo(db):
    md_titulo = "# Pences\nTexto sobre outro assunto qualquer."
    md_corpo = "# Outro\nAqui se fala de pences no meio do texto."
    ingest_document(
        db, source_id="t", name="titulo.md", mime_type="text/markdown",
        modified_time="1", data=md_titulo.encode(),
    )
    ingest_document(
        db, source_id="c", name="corpo.md", mime_type="text/markdown",
        modified_time="1", data=md_corpo.encode(),
    )
    assert search(db, "pences")[0].document_name == "titulo.md"


def test_hit_traz_pagina_titulo_e_texto(db):
    ingest_document(
        db, source_id="m", name="aula.md", mime_type="text/markdown",
        modified_time="1", data=b"# Bainha\nA bainha embutida fecha a barra.",
    )
    hit = search(db, "bainha")[0]
    assert (hit.document_name, hit.heading, hit.page) == ("aula.md", "Bainha", None)
    assert "barra" in hit.text


def test_filtra_por_documentos(db):
    a = indexar(db, "a", "a.txt", "Texto sobre saia.")
    indexar(db, "b", "b.txt", "Outro texto sobre saia.")
    hits = search(db, "saia", document_ids=[a.document_id])
    assert [h.document_name for h in hits] == ["a.txt"]
    assert search(db, "saia", document_ids=[]) == []


def test_limita_a_k_resultados(db):
    for i in range(5):
        indexar(db, f"d{i}", f"d{i}.txt", "saia saia saia")
    assert len(search(db, "saia", k=3)) == 3
    assert search(db, "saia", k=0) == []


def test_consulta_vazia_nao_busca(db):
    indexar(db, "a", "a.txt", "algo")
    assert search(db, "") == []
