# StudyLoop Lite

Mentor de estudos local que lê seus materiais do Google Drive e usa a sua chave da API Claude.
Recomeço mais leve do StudyLoop.

Escopo, arquitetura e marcos: veja [`SPEC.md`](SPEC.md).

## Status

- **M0** (esqueleto): API FastAPI com `/health` e `/chat`, configuração por `.env`, SQLite e
  `ClaudeProvider`.
- **M1a** (ingestão e busca): extração de texto (txt, md, pdf, docx), chunks, índice FTS5 e
  busca com citação de arquivo, página e título. Drive (M1b), mentor com RAG, quizzes e mapas
  mentais vêm nos próximos marcos.

## Começando

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env        # preencha ANTHROPIC_API_KEY
uvicorn studyloop.main:app --reload
```

A chave da API é cobrada à parte da assinatura do Claude.ai (crie em console.anthropic.com).
O `.env` está no `.gitignore`: nunca versione a chave.
