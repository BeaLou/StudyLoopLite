from studyloop.ingest.chunk import MAX_WORDS, OVERLAP_WORDS, chunk_sections
from studyloop.ingest.extract import Section


def palavras(n: int, prefixo: str = "p") -> str:
    return " ".join(f"{prefixo}{i}" for i in range(n))


def paragrafos(qtd: int, tamanho: int = 100) -> str:
    return "\n\n".join(palavras(tamanho, f"par{i}_") for i in range(qtd))


def test_texto_curto_vira_um_trecho():
    chunks = chunk_sections([Section(text="Moulage é uma técnica de modelagem.")])
    assert [c.text for c in chunks] == ["Moulage é uma técnica de modelagem."]


def test_sem_texto_nao_gera_trechos():
    assert chunk_sections([]) == []
    assert chunk_sections([Section(text="  \n\n  ")]) == []


def test_texto_longo_e_dividido_em_varios_trechos_de_tamanho_limitado():
    chunks = chunk_sections([Section(text=paragrafos(20))])  # 2000 palavras
    assert len(chunks) > 3
    for chunk in chunks:
        assert len(chunk.text.split()) <= MAX_WORDS + OVERLAP_WORDS


def test_trechos_consecutivos_se_sobrepoem():
    chunks = chunk_sections([Section(text=paragrafos(20))])
    for anterior, atual in zip(chunks, chunks[1:], strict=False):
        cauda = anterior.text.split()[-OVERLAP_WORDS:]
        assert atual.text.split()[:OVERLAP_WORDS] == cauda


def test_sem_sobreposicao_quando_desligada():
    chunks = chunk_sections([Section(text=paragrafos(20))], overlap_words=0)
    todas = " ".join(c.text for c in chunks).split()
    assert todas == paragrafos(20).split()


def test_nenhum_conteudo_se_perde():
    texto = paragrafos(12, tamanho=90)
    chunks = chunk_sections([Section(text=texto)], overlap_words=0)
    assert " ".join(c.text for c in chunks).split() == texto.split()


def test_trecho_nao_atravessa_paginas_nem_titulos():
    secoes = [
        Section(text=palavras(30, "a"), page=1, heading="Intro"),
        Section(text=palavras(30, "b"), page=2, heading="Intro"),
        Section(text=palavras(30, "c"), page=None, heading="Costura"),
    ]
    chunks = chunk_sections(secoes)
    assert [(c.page, c.heading) for c in chunks] == [(1, "Intro"), (2, "Intro"), (None, "Costura")]
    assert all(c.text.split()[0].startswith(p) for c, p in zip(chunks, "abc", strict=True))


def test_paragrafo_gigante_sem_pontuacao_e_quebrado():
    chunks = chunk_sections([Section(text=palavras(2000))], overlap_words=0)
    assert len(chunks) >= 4
    assert all(len(c.text.split()) <= MAX_WORDS for c in chunks)


def test_paragrafo_gigante_e_quebrado_preferindo_frases():
    frase = palavras(30, "x") + "."
    chunks = chunk_sections([Section(text=" ".join([frase] * 40))], overlap_words=0)
    assert len(chunks) > 1
    assert all(c.text.endswith(".") for c in chunks)
