# CLAUDE.md — StudyLoop Lite

Leia `SPEC.md` antes de qualquer tarefa. Ele é a fonte da verdade do escopo.

## Contexto

App local de estudos para autodidatas: lê arquivos escolhidos no Google Drive, faz RAG por
palavra-chave (SQLite FTS5) e oferece mentor, quizzes e mapas mentais usando a API da Claude
(chave do próprio usuário). A dona do projeto é a Bea (dev full-stack, C#/.NET e JavaScript;
nesta stack, Python). Comunicação em português do Brasil.

## Regras de trabalho

- Uma tarefa por vez, alinhada a um marco do `SPEC.md` (M0 a M4). Não adiantar marcos.
- Trabalhar em branch e abrir PR; nunca commitar direto na `main` depois do bootstrap.
- Commits pequenos, mensagens em português no imperativo (ex.: `Adiciona ClaudeProvider`).
- Mudou o escopo ou uma decisão? Atualizar o `SPEC.md` no mesmo PR.
- Se algo do `SPEC.md` estiver ambíguo, perguntar antes de decidir. Listar a dúvida na seção 11 e, ao ser respondida, registrar a decisão na seção 10.

## Restrições que não podem ser quebradas

- Sem Docker, sem nuvem, sem embeddings no início, sem Ollama (fase 2).
- Não salvar arquivos originais no disco: só texto extraído e chunks.
- Chave da API somente em variável de ambiente. Nunca no código, no frontend, em logs ou no repo.
- Escopo do Drive: `drive.file` com Picker.
- Não mandar documentos inteiros ao modelo: só os trechos recuperados.
- IDs de modelo ficam em configuração, nunca espalhados no código.

## Convenções de código

- Python 3.12+, tipagem em todas as funções públicas, `ruff` para lint e formato.
- Módulos conforme a arquitetura do `SPEC.md`: `drive/`, `ingest/`, `rag/`, `llm/`, `mentor/`, `quiz/`, `mindmap/`.
- Todo acesso ao modelo passa por `LLMProvider`. Nenhum módulo importa `anthropic` diretamente, a não ser `llm/`.
- Saídas estruturadas da IA (quiz, mapa) são validadas por schema antes de uso.
- Registrar `usage` (tokens, cache) de cada chamada à Claude.

## Testes

- `pytest`. Chamadas à Claude e ao Google sempre mockadas; nenhum teste usa rede ou chave real.
- Cada marco entrega testes dos fluxos principais antes do PR.

## Segurança

- `.env` no `.gitignore`; manter `.env.example` atualizado.
- Antes de cada PR: `git grep -nEi "sk-ant|api[_-]?key|client_secret"` não deve achar segredos.
- Logs sem conteúdo de documentos.

## Como rodar

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env        # preencher ANTHROPIC_API_KEY
uvicorn studyloop.main:app --reload
pytest
ruff check . && ruff format --check .
```

Teste manual do M0:

```bash
curl http://127.0.0.1:8000/health
curl -X POST http://127.0.0.1:8000/chat -H "Content-Type: application/json" \
  -d '{"message": "Explique o que é uma moulage em duas frases."}'
```
