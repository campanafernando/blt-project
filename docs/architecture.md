# Arquitetura — decisões de implementação

## Camadas

```
HTTP ──▶ View ──▶ Serializer ──▶ Service ──▶ Model
                                   │
                                   └──▶ Selector ──▶ QuerySet
```

| Camada | Arquivo | Pode | Não pode |
|---|---|---|---|
| View | `tasks/views.py`, `hypermedia/views.py` | Validar entrada, escolher status HTTP, chamar serviço | Conhecer ORM, decidir regra |
| Serializer | `tasks/serializers.py` | Validar contrato, montar saída | Escrever no banco direto |
| Service | `tasks/services.py` | Regra, transição de estado, agendar efeito | Montar resposta HTTP |
| Selector | `tasks/selectors.py` | Escopo de visibilidade, agregações | Alterar dados |
| Model | `tasks/models.py` | Invariante de dado, propriedade derivada | Conhecer request |

## Visibilidade

`tasks_for(user)` retorna `created_by = user OR assigned_to = user`. O detalhe usa o
mesmo escopo, então uma tarefa de outro usuário responde **404**, não 403. Isso evita
confirmar a existência do recurso.

Excluir é a única ação restrita ao criador (403 quando o usuário é apenas responsável).

## Transições de status

Toda mudança passa por `services`. A regra:

- concluir quando já está concluída → não altera `completed_at` (idempotente)
- reabrir quando não está concluída → no-op
- mudar para `done` via PATCH → define `completed_at`
- sair de `done` → limpa `completed_at`

As três entradas (endpoint dedicado, PATCH, HTMX) usam o mesmo serviço.

## Notificação

`transaction.on_commit` agenda `notify_assignment.delay(task_id)`. Se a transação
falhar, não existe e-mail de tarefa que não foi salva. Em teste, o callback é capturado
por `django_capture_on_commit_callbacks`.

O envio não bloqueia a resposta: a API devolve 201 mesmo se o broker estiver lento. Se
o broker estiver fora, o erro aparece no log do processo após o commit, não no request.

## `is_overdue`

Derivado, não persistido. Evita job noturno e estado inconsistente. O filtro
`overdue=true` replica a mesma regra em SQL (`due_date < hoje AND status != done`).

## Dois clientes, uma regra

O cliente HTMX importa `TaskCreateSerializer` e os serviços. O formulário usa os mesmos
nomes de campo da API. A resposta de criação devolve:

1. o formulário resetado (target `#task-form`)
2. as linhas atualizadas via `hx-swap-oob`
3. `HX-Trigger: task-created` para o Alpine fechar o dialog

Nenhum estado de lista é mantido no Alpine. Ele só guarda o dialog aberto/fechado.

## Autenticação

| Cliente | Mecanismo |
|---|---|
| React | JWT no header `Authorization`, refresh single-flight em `web/src/lib/api.ts` |
| HTMX | Sessão Django, CSRF no formulário e em `hx-headers` |

Os dois coexistem porque o DRF usa JWT como autenticador padrão e as views de template
usam `login_required`. O admin usa sessão.

## Por que `APIView` e não `ViewSet`

ViewSet esconde o mapa de endpoints atrás de um router. Aqui cada operação é uma classe
com um método e um `@extend_schema`. Em code review, "o que `POST /tasks/1/complete/`
faz" se responde lendo 15 linhas. O custo é mais classes; o ganho é explicabilidade.

## Banco

PostgreSQL em Compose e CI; SQLite quando `DB_ENGINE` não é `postgres`. A decisão existe
para o revisor rodar `make setup && make test` sem Docker. Nenhuma feature depende de
SQL específico de Postgres.

## Falhas conhecidas

- `page_size` é validado pelo paginador, não pelo schema.
- Não há lock otimista: duas edições concorrentes aplicam last-write-wins.
- O digest diário envia e-mail por tarefa, não um agregado por pessoa.
