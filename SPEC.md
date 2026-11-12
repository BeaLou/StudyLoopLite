# StudyLoop Lite — SPEC (v2)

> Recomeço do StudyLoop: mais leve, mais funcional. Um mentor de estudos que lê os
> seus materiais do Google Drive e usa a sua chave da API Claude.

## 1. Objetivo

Ajudar autodidatas a estudar a partir dos próprios materiais. O usuário escolhe arquivos do
Drive, e o app oferece:

1. **Mentor**: chat que responde com base nos materiais, cita arquivo e trecho, e sugere o próximo passo.
2. **Quizzes**: perguntas geradas a partir dos materiais, com correção e histórico.
3. **Mapas mentais**: visão hierárquica de um arquivo ou tema.

Caso de uso inicial: estudos de design de moda (moulage, patternmaking, croqui, spec sheet etc.).
O app deve ser genérico, sem nada fixo de moda no código.

## 2. Restrições (decididas)

| Restrição | Decisão |
|---|---|
| Execução | Somente local. Sem Docker, sem nuvem. |
| Disco | Não guardar arquivos originais. Guardar só texto extraído e chunks. |
| IA | API da Claude com chave do próprio usuário (BYOK), SDK `anthropic`. |
| Chave | Variável de ambiente lida no backend. Nunca no frontend, nunca no repo. |
| Fontes | Google Drive via Google Picker, escopo `drive.file`. |
| RAG | Busca por palavra-chave (SQLite FTS5/BM25). Sem embeddings no início. |
| LLM local | Fase 2 (Ollama), via interface `LLMProvider`. |
| Idioma | Interface e respostas em português do Brasil por padrão. |

## 3. Fora de escopo (por enquanto)

Multiagentes, login multiusuário, deploy em nuvem, Docker, embeddings/vetores, Ollama,
aplicação a idiomas, repetição espaçada completa.

## 4. Arquitetura

```
 Navegador (frontend leve)
   |  Google Picker  --> escolhe arquivos do Drive
   |  chat / quiz / mapa mental
   v
 FastAPI (processo único)
   |-- drive/        OAuth + download/export de arquivos selecionados
   |-- ingest/       extração de texto -> chunks -> índice FTS5
   |-- rag/          busca (BM25) + montagem de contexto com fontes
   |-- llm/          LLMProvider (ClaudeProvider hoje; OllamaProvider na fase 2)
   |-- mentor/       prompt do mentor, memória do plano de estudos
   |-- quiz/         geração (JSON), correção, histórico
   |-- mindmap/      geração de outline, entrega p/ renderização
   v
 SQLite (arquivo único): documentos, chunks, FTS, conversas, plano, quizzes, resultados
```

### Stack

- **Backend:** Python 3.12+, FastAPI, `anthropic`, SQLite (FTS5), `pypdf`, `python-docx`.
- **Frontend:** HTML + JavaScript puro (módulos ES), servido pelo próprio FastAPI, sem etapa de build. Mapas via Markmap ou Mermaid.
- **Testes:** pytest. Chamadas à Claude sempre mockadas nos testes.

### Interface de LLM

```python
class LLMProvider(Protocol):
    def chat(self, system: str, messages: list[Message], *, model_tier: str) -> str: ...
    def structured(self, system: str, messages: list[Message], schema: dict) -> dict: ...
```

`model_tier` aceita `"cheap"` (Haiku) e `"smart"` (Sonnet). Os IDs reais dos modelos ficam em
configuração, nunca espalhados no código.

## 5. Funcionalidades

### 5.1 Fontes (Drive)
- Conectar a conta Google (OAuth, escopo `drive.file`) e escolher arquivos pelo Picker.
- Tipos: Google Docs, Google Sheets (como texto), PDF, DOCX, TXT/MD.
- Google Docs são exportados como texto pela API. Os demais são baixados em memória, extraídos e descartados.
- Re-sincronizar um arquivo atualiza seus chunks (compara `modifiedTime`).
- A atualização é **incremental por documento**: se `modifiedTime` mudou, apaga os chunks daquele documento e insere os novos em uma transação. Os demais documentos não são tocados.

### 5.2 Ingestão e busca
- Chunks de ~500–800 tokens com pequena sobreposição, guardando `documento`, `posição` e `título/página` quando houver.
- Índice FTS5 com tokenizador sem acentos (`unicode61 remove_diacritics 2`).
- Consulta: o mentor reescreve a pergunta em termos de busca, pega o top-k (padrão 6) e monta o contexto.
- **Limite de contexto:** mandar apenas os trechos recuperados, nunca documentos inteiros.

### 5.3 Mentor
- Responde só com base nos trechos recuperados. Se não houver base, diz isso e pode responder com conhecimento geral **sinalizando**.
- Toda afirmação baseada em material traz citação `[arquivo, trecho]`.
- Memória: objetivo do usuário, módulo atual, tópicos já estudados, pontos fracos (vindos dos quizzes).
- **Plano de estudos = lista estruturada de módulos.** Cada módulo tem título, descrição, ordem, status (`a_fazer`, `em_andamento`, `concluido`) e, opcionalmente, arquivos associados. O usuário edita a lista e o mentor pode propor módulos e mudanças de status, que o usuário confirma.
- Ação "o que estudar agora?": sugere próximo passo com base no plano e no histórico.
- Prompt caching no prompt de sistema e no plano de estudos.

### 5.4 Quizzes
- Entrada: arquivo ou tema, número de perguntas, dificuldade.
- Saída da IA em JSON validado por schema: múltipla escolha e resposta curta, com gabarito e explicação.
- App corrige, guarda acertos/erros por tópico e alimenta a memória do mentor.

### 5.5 Mapas mentais
- Entrada: arquivo ou tema.
- Saída da IA: outline hierárquico em Markdown (ou JSON de árvore).
- Frontend renderiza com Markmap/Mermaid. Exportar como Markdown ou SVG.

## 6. Custos e modelos

- `cheap` (Haiku): extração, resumo, quiz, mapa mental, reescrita de consulta.
- `smart` (Sonnet): respostas do mentor e sugestões de plano.
- Prompt caching nos blocos fixos. Registrar `usage` de cada chamada e mostrar uso estimado na interface.
- Atenção ao degrau de preço do Haiku acima de 100 mil tokens de prompt: o RAG evita isso por construção.

## 7. Segurança e privacidade

- Chave da API apenas em `.env` (ignorado pelo git). Fornecer `.env.example`.
- Tokens OAuth do Google guardados localmente e fora do repo.
- Pedir o menor escopo possível (`drive.file`).
- Logs não registram conteúdo dos documentos nem a chave.

## 8. Marcos

| Marco | Entrega | Pronto quando |
|---|---|---|
| **M0** | Esqueleto: FastAPI, SQLite, config, `LLMProvider` + `ClaudeProvider`, endpoint `/health` e `/chat` simples | Rodar localmente e conversar com a Claude; testes passando |
| **M1** | Drive + ingestão: OAuth, Picker, extração, chunks, FTS5 | Selecionar arquivos do Drive e buscar trechos por palavra-chave |
| **M2** | Mentor com RAG: citações, memória do plano, "o que estudar agora?" | Respostas citam fontes; plano persiste entre sessões |
| **M3** | Quizzes: geração, correção, histórico por tópico | Quiz de um arquivo, com resultado salvo e usado pelo mentor |
| **M4** | Mapas mentais: geração, render, exportação | Mapa de um arquivo renderizado e exportável |
| **Fase 2** | `OllamaProvider`; avaliar embeddings se o BM25 ficar fraco | Trocar de provedor por configuração |

## 9. Critérios de aceite do MVP (M0–M2)

1. Escolho 2+ arquivos do Drive e eles ficam pesquisáveis, sem originais salvos no disco.
2. Pergunto algo sobre o material e recebo resposta com citação do arquivo.
3. Pergunto "o que estudar agora?" e recebo um próximo passo coerente com o plano.
4. Nada de segredo no repo; `git grep` por chaves não retorna nada.

## 10. Decisões registradas

- **Frontend:** HTML/JS puro, sem build (mais leve; pode migrar depois se a interface crescer).
- **Plano de estudos:** lista estruturada de módulos (ver 5.3).
- **Índice FTS:** atualização incremental por documento, em transação (ver 5.1). Reconstrução total só como comando de manutenção.

## 11. Perguntas em aberto

- (nenhuma no momento)
