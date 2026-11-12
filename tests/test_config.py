from pathlib import Path

from studyloop.config import (
    DEFAULT_DB_PATH,
    DEFAULT_MAX_TOKENS,
    DEFAULT_MODEL_CHEAP,
    DEFAULT_MODEL_SMART,
    load_dotenv,
    load_settings,
)


def test_defaults_sem_variaveis():
    s = load_settings({})
    assert s.anthropic_api_key is None
    assert s.db_path == Path(DEFAULT_DB_PATH)
    assert s.models == {"cheap": DEFAULT_MODEL_CHEAP, "smart": DEFAULT_MODEL_SMART}
    assert s.max_tokens == DEFAULT_MAX_TOKENS


def test_le_variaveis_do_ambiente():
    s = load_settings(
        {
            "ANTHROPIC_API_KEY": "  chave-de-teste  ",
            "STUDYLOOP_DB_PATH": "/tmp/x.db",
            "STUDYLOOP_MODEL_CHEAP": "modelo-barato",
            "STUDYLOOP_MODEL_SMART": "modelo-bom",
            "STUDYLOOP_MAX_TOKENS": "256",
        }
    )
    assert s.anthropic_api_key == "chave-de-teste"
    assert s.db_path == Path("/tmp/x.db")
    assert s.models == {"cheap": "modelo-barato", "smart": "modelo-bom"}
    assert s.max_tokens == 256


def test_chave_vazia_vira_none():
    assert load_settings({"ANTHROPIC_API_KEY": "   "}).anthropic_api_key is None


def test_repr_nao_vaza_a_chave():
    s = load_settings({"ANTHROPIC_API_KEY": "segredo-123"})
    assert "segredo-123" not in repr(s)
    assert "segredo-123" not in str(s)


def test_load_dotenv_nao_sobrescreve_ambiente(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "# comentário\nANTHROPIC_API_KEY='do-arquivo'\nOUTRA=valor\n\nlinha-invalida\n",
        encoding="utf-8",
    )
    environ = {"OUTRA": "do-ambiente"}
    load_dotenv(env_file, environ)
    assert environ["ANTHROPIC_API_KEY"] == "do-arquivo"
    assert environ["OUTRA"] == "do-ambiente"


def test_load_dotenv_arquivo_ausente(tmp_path):
    environ: dict[str, str] = {}
    load_dotenv(tmp_path / "nao-existe.env", environ)
    assert environ == {}
