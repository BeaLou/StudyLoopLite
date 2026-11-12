from studyloop.db import Database


def test_init_cria_pasta_e_tabela(tmp_path):
    db = Database(tmp_path / "sub" / "app.db")
    db.init()
    assert (tmp_path / "sub" / "app.db").exists()
    assert db.usage_totals()["calls"] == 0


def test_init_cria_tabelas_de_ingestao_e_indice(tmp_path):
    db = Database(tmp_path / "app.db")
    db.init()
    with db.connect() as conn:
        nomes = {r[0] for r in conn.execute("SELECT name FROM sqlite_master")}
    assert {"documents", "chunks", "chunks_fts", "usage"} <= nomes


def test_chaves_estrangeiras_ativas(tmp_path):
    db = Database(tmp_path / "app.db")
    db.init()
    with db.connect() as conn:
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1


def test_init_e_idempotente(tmp_path):
    db = Database(tmp_path / "app.db")
    db.init()
    db.init()


def test_registra_e_soma_uso(tmp_path):
    db = Database(tmp_path / "app.db")
    db.init()
    db.record_usage("m1", 100, 20, cache_read_tokens=50, cache_creation_tokens=10)
    db.record_usage("m2", 30, 5)
    assert db.usage_totals() == {
        "calls": 2,
        "input_tokens": 130,
        "output_tokens": 25,
        "cache_read_tokens": 50,
        "cache_creation_tokens": 10,
    }
