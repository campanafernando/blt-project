# BLT project — regras para agentes

## Estrutura

- `api/` — Django 6 + DRF. App de domínio em `tasks/`, autenticação em `accounts/`.
- `api/hypermedia/` — cliente HTMX + Alpine. Não tem regra de negócio.
- `web/` — React + Vite. `src/lib/api.ts` é a única camada HTTP.

## Fronteiras

- View só valida, chama serviço e responde. Nunca consulta ORM direto para regra.
- Regra em `tasks/services.py`; consulta em `tasks/selectors.py`; filtro em `tasks/filters.py`.
- `hypermedia` chama os mesmos serviços e serializers. Proibido duplicar validação.
- Componente React não monta URL nem lê token. Use `apiFetch` e os hooks de features.

## Qualidade

- `make test` exige cobertura ≥ 80%.
- `make check` roda ruff, pytest, schema e build do front.
- Erro de API segue o formato do DRF; o front lê `detail` e mapa campo → lista.
- Nada de warning no console do navegador.

## Operação

- Local: SQLite + cache em memória + Celery eager, sem Docker.
- Compose: Postgres, Redis, Mailpit, API, worker, beat, web. MinIO em profile `storage`.
- Segredos só no `.env`. `.env.example` documenta todas as chaves.

## Proibido

- Commitar sem autorização.
- Duplicar regra entre API e HTMX.
- Adicionar dependência sem necessidade demonstrada.
- Deixar `manage.py check`, ruff ou `tsc` com erro.
