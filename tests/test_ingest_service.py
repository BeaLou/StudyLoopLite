import pytest
from helpers import make_docx

from studyloop.db import Database
from studyloop.ingest.extract import EmptyDocument, UnsupportedFileType
from studyloop.ingest.service import ingest_document, list_documents, remove_document
from studyloop.rag.search import search


@pytest.fixture
def db(tmp_path):
    database = Database(tmp_path / "app.db")
    database.init()
    return database


def ingest(
    db, texto, *, source_id="drive:1", name="aula.txt", modified="2026-01-01", mime="text/plain"
):
    return ingest_document(
        db, source_id=source_id, name=name, mime_type=mime,
        modified_time=modified, data=texto if isinstance(texto, bytes) else texto.encode(),
    )


def test_cria_documento_e_trechos(db):
    r = ingest(db, "Moulage no manequim.")
    assert (r.status, r.chunk_count) == ("created", 1)
    docs = list_documents(db)
    resumo = [(d["source_id"], d["name"], d["chunk_count"]) for d in docs]
    assert resumo == [("drive:1", "aula.txt", 1)]


def test_mesmo_modified_time_nao_reprocessa(db):
    ingest(db, "Texto original sobre saia.")
    # Bytes inválidos provam que a extração nem foi tentada.
    r = ingest(db, b"\x00\x01 lixo", mime="application/pdf", name="aula.pdf")
    assert r.status == "unchanged"
    assert search(db, "saia")


def test_modified_time_novo_troca_os_trechos(db):
    ingest(db, "Texto antigo sobre bainha.", modified="1")
    r = ingest(db, "Texto novo sobre pences.", modified="2")
    assert r.status == "updated"
    assert search(db, "bainha") == []
    assert [h.document_name for h in search(db, "pences")] == ["aula.txt"]
    assert len(list_documents(db)) == 1


def test_atualizar_nao_mexe_nos_outros_documentos(db):
    ingest(db, "Saia godê.", source_id="a", name="a.txt")
    outro = ingest(db, "Calça pantalona.", source_id="b", name="b.txt")
    ingest(db, "Saia lápis.", source_id="a", name="a.txt", modified="novo")
    assert [h.document_id for h in search(db, "pantalona")] == [outro.document_id]
    assert {d["name"]: d["chunk_count"] for d in list_documents(db)} == {"a.txt": 1, "b.txt": 1}


def test_sem_modified_time_sempre_reprocessa(db):
    ingest(db, "Primeira versão.", modified=None)
    assert ingest(db, "Segunda versão.", modified=None).status == "updated"


def test_atualizacao_atualiza_o_nome(db):
    ingest(db, "conteudo", name="velho.txt", modified="1")
    ingest(db, "conteudo", name="novo.txt", modified="2")
    assert [d["name"] for d in list_documents(db)] == ["novo.txt"]


def test_remover_tira_documento_e_busca(db):
    ingest(db, "Texto sobre croqui.")
    assert remove_document(db, "drive:1") is True
    assert list_documents(db) == []
    assert search(db, "croqui") == []
    assert remove_document(db, "drive:1") is False


def test_arquivo_nao_suportado_nao_deixa_rastro(db):
    with pytest.raises(UnsupportedFileType):
        ingest(db, b"MZ", name="x.exe", mime="application/octet-stream")
    assert list_documents(db) == []


def test_arquivo_vazio_nao_deixa_rastro(db):
    with pytest.raises(EmptyDocument):
        ingest(db, "   ")
    assert list_documents(db) == []


def test_falha_na_atualizacao_preserva_a_versao_anterior(db):
    ingest(db, "Versão boa sobre moulage.", modified="1")
    with pytest.raises(EmptyDocument):
        ingest(db, "   ", modified="2")
    assert search(db, "moulage")
    assert list_documents(db)[0]["chunk_count"] == 1


def test_original_nao_e_guardado_no_banco(db, tmp_path):
    docx = make_docx([("h", "Título"), ("p", "Corpo do documento sobre modelagem.")])
    ingest(db, docx, name="aula.docx", mime="")
    assert docx[:60] not in (tmp_path / "app.db").read_bytes()
    assert search(db, "modelagem")


def test_documento_grande_gera_varios_trechos_numerados(db):
    texto = "\n\n".join(" ".join(f"w{p}_{i}" for i in range(120)) for p in range(15))
    r = ingest(db, texto)
    assert r.chunk_count > 1
    with db.connect() as conn:
        posicoes = [row[0] for row in conn.execute("SELECT position FROM chunks ORDER BY id")]
    assert posicoes == list(range(r.chunk_count))
