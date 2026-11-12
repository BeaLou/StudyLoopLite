from types import SimpleNamespace

import pytest

from studyloop.llm.claude import ClaudeProvider

MODELS = {"cheap": "haiku-fake", "smart": "sonnet-fake"}


class FakeMessages:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self.response


class FakeClient:
    def __init__(self, response):
        self.messages = FakeMessages(response)


def make_response(*texts, usage=None):
    blocks = [SimpleNamespace(type="text", text=t) for t in texts]
    return SimpleNamespace(content=blocks, usage=usage)


def test_chat_devolve_texto_e_usa_o_modelo_do_nivel():
    client = FakeClient(make_response("Olá, ", "mundo!"))
    provider = ClaudeProvider(client, MODELS, max_tokens=321)

    reply = provider.chat("sistema", [{"role": "user", "content": "oi"}], model_tier="smart")

    assert reply == "Olá, mundo!"
    call = client.messages.calls[0]
    assert call["model"] == "sonnet-fake"
    assert call["max_tokens"] == 321
    assert call["messages"] == [{"role": "user", "content": "oi"}]


def test_chat_marca_o_sistema_para_cache():
    client = FakeClient(make_response("ok"))
    provider = ClaudeProvider(client, MODELS)
    provider.chat("regras", [{"role": "user", "content": "x"}], model_tier="cheap")

    system = client.messages.calls[0]["system"]
    assert system == [{"type": "text", "text": "regras", "cache_control": {"type": "ephemeral"}}]
    assert client.messages.calls[0]["model"] == "haiku-fake"


def test_chat_ignora_blocos_que_nao_sao_texto():
    response = SimpleNamespace(
        content=[SimpleNamespace(type="tool_use"), SimpleNamespace(type="text", text="só isto")],
        usage=None,
    )
    provider = ClaudeProvider(FakeClient(response), MODELS)
    assert provider.chat("s", [{"role": "user", "content": "x"}], model_tier="smart") == "só isto"


def test_registra_uso_via_callback():
    usage = SimpleNamespace(
        input_tokens=10,
        output_tokens=4,
        cache_read_input_tokens=7,
        cache_creation_input_tokens=None,
    )
    registrados = []
    provider = ClaudeProvider(
        FakeClient(make_response("ok", usage=usage)), MODELS, on_usage=registrados.append
    )

    provider.chat("s", [{"role": "user", "content": "x"}], model_tier="smart")

    assert len(registrados) == 1
    u = registrados[0]
    assert (u.model, u.input_tokens, u.output_tokens) == ("sonnet-fake", 10, 4)
    assert (u.cache_read_tokens, u.cache_creation_tokens) == (7, 0)


def test_nivel_desconhecido_levanta_erro():
    provider = ClaudeProvider(FakeClient(make_response("ok")), MODELS)
    with pytest.raises(ValueError, match="desconhecido"):
        provider.chat("s", [{"role": "user", "content": "x"}], model_tier="enorme")  # type: ignore


def test_structured_ainda_nao_implementado():
    provider = ClaudeProvider(FakeClient(make_response("ok")), MODELS)
    with pytest.raises(NotImplementedError):
        provider.structured("s", [], {}, model_tier="cheap")
