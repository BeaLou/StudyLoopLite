import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from studyloop.config import load_settings  # noqa: E402
from studyloop.main import create_app  # noqa: E402


class FakeProvider:
    def __init__(self):
        self.calls = []

    def chat(self, system, messages, *, model_tier):
        self.calls.append((system, messages, model_tier))
        return "resposta falsa"

    def structured(self, system, messages, schema, *, model_tier):
        raise NotImplementedError


@pytest.fixture
def settings(tmp_path):
    return load_settings({"STUDYLOOP_DB_PATH": str(tmp_path / "t.db")})


def test_health(settings):
    client = TestClient(create_app(settings, provider=FakeProvider()))
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_chat_envia_historico_e_usa_nivel_smart(settings):
    provider = FakeProvider()
    client = TestClient(create_app(settings, provider=provider))

    r = client.post(
        "/chat",
        json={
            "message": "e agora?",
            "history": [
                {"role": "user", "content": "oi"},
                {"role": "assistant", "content": "olá"},
            ],
        },
    )

    assert r.status_code == 200
    assert r.json() == {"reply": "resposta falsa"}
    _, messages, tier = provider.calls[0]
    assert tier == "smart"
    assert [m["content"] for m in messages] == ["oi", "olá", "e agora?"]
    assert messages[-1]["role"] == "user"


def test_chat_sem_chave_devolve_503(settings):
    client = TestClient(create_app(settings))
    r = client.post("/chat", json={"message": "oi"})
    assert r.status_code == 503
    assert "ANTHROPIC_API_KEY" in r.json()["detail"]


def test_chat_rejeita_mensagem_vazia(settings):
    client = TestClient(create_app(settings, provider=FakeProvider()))
    assert client.post("/chat", json={"message": ""}).status_code == 422


def test_documents_e_search(settings):
    from studyloop.ingest.service import ingest_document

    app = create_app(settings, provider=FakeProvider())
    ingest_document(
        app.state.database, source_id="a", name="aula.md", mime_type="text/markdown",
        modified_time="1", data=b"# Moulage\nTecnica de modelagem sobre o manequim.",
    )
    client = TestClient(app)

    docs = client.get("/documents").json()
    assert [(d["name"], d["chunk_count"]) for d in docs] == [("aula.md", 1)]

    hits = client.get("/search", params={"q": "manequim"}).json()
    assert hits[0]["document_name"] == "aula.md"
    assert hits[0]["heading"] == "Moulage"
    assert client.get("/search", params={"q": "zzz"}).json() == []


def test_search_valida_parametros(settings):
    client = TestClient(create_app(settings, provider=FakeProvider()))
    assert client.get("/search").status_code == 422
    assert client.get("/search", params={"q": "x", "k": 0}).status_code == 422
    assert client.get("/search", params={"q": "x", "k": 99}).status_code == 422


def test_chat_rejeita_papel_invalido_no_historico(settings):
    client = TestClient(create_app(settings, provider=FakeProvider()))
    r = client.post(
        "/chat", json={"message": "oi", "history": [{"role": "system", "content": "x"}]}
    )
    assert r.status_code == 422
