# Demo — roteiro de 5 minutos

Objetivo: mostrar decisão, não tela. Cada bloco tem uma frase de arquitetura.

## 1. Abertura (40s)

> This is BLT, a task manager with two clients on one API. The React client is the
> required deliverable; the HTMX client is a bonus because your stack is hypermedia-first.
> The important part is that both call the same service layer — the rule exists once.

Abrir o board React já logado.

## 2. React + contrato (90s)

- Filtrar por status e por data. Mostrar paginação.
- Criar uma tarefa atribuída à Maria.
- Abrir o Mailpit e mostrar o e-mail que o **worker Celery** enviou.
- Frase: *"A API devolve 201 antes do e-mail sair; o envio é agendado com `on_commit`,
  então uma transação que falha não gera notificação."*

## 3. Código — a fronteira (90s)

Abrir `api/tasks/views.py`, `services.py`, `selectors.py` nesta ordem.

> The view only validates and calls the service. The service owns the rule. The selector
> owns what a user can see. That is why the HTMX view below can reuse both.

Abrir `api/hypermedia/views.py` e mostrar que importa `tasks.services`.

## 4. HTMX + Alpine (70s)

Abrir `/app/`.

- Filtrar (partial swap).
- Criar tarefa pelo dialog: mostrar a resposta com `hx-swap-oob` no DevTools.
- Concluir uma linha: swap de uma `<tr>`.
- Frase: *"Alpine guarda só o dialog aberto. Nenhum estado de lista no cliente."*

## 5. Spec from issue (60s, se houver tempo)

- Abrir a aba **Spec**, colar a URL da issue #1.
- Mostrar a spec gerada: critérios, passos, riscos, tamanho, latência.
- Clicar em **Publicar como issue** e abrir o link criado.
- Frase: *"The input is a URL, not a prompt. The model returns a JSON contract that we
  validate; anything else is a 502. The issue body is treated as untrusted data."*
- Mencionar o MCP: *"The same flow is available in the terminal through four MCP tools."*

## 6. Qualidade e IA (60s)

- `make test` → 54 testes, 97%.
- Mostrar um teste de borda: `test_complete_is_idempotent`.
- Abrir `docs/ai/02-review.md` e contar **um** defeito que a IA introduziu e você pegou
  rodando o código (schema inválido ou 404/403).
- Frase: *"The prompt set the rules; the failures were in what the prompt did not say —
  global cache between tests, container permissions, HTTP status parity."*

## Perguntas que você deve puxar

- "Why not a ViewSet?" → explicabilidade do mapa de endpoints.
- "Why SQLite default?" → revisor roda sem Docker; CI roda Postgres.
- "Why two clients?" → provar que a regra não está presa ao DRF.

## O que não mostrar

- Não abra `admin/` a menos que perguntem.
- Não mostre o MinIO profile; mencione em uma frase se perguntarem de infra.
- Não defenda `localStorage` como ideal; diga que é trade-off documentado.
