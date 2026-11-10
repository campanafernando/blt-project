# Prompt — scaffold da API

Ferramenta: OpenCode, modelo `deepseek-v4.1-flash`, com o workspace ANA/LOGUS aberto
como referência de convenções. O objetivo do prompt era gerar estrutura, não regra:
regra foi escrita e revisada à mão.

## Prompt principal

```text
You are scaffolding a Django 6 + DRF service. Write code, do not explain.

Context
- Python 3.12, Django 6.0, DRF 3.18, SimpleJWT, drf-spectacular, django-filter.
- Project root: blt-project/api. Settings in config/settings.py, env via python-dotenv.
- Domain: Task(id, title, description, status[todo|in_progress|done], due_date,
  assigned_to FK User null, created_by FK User, completed_at, created_at, updated_at).
- Business rules:
  1. A user sees tasks they created or that are assigned to them.
  2. Only the creator can delete.
  3. Completing an already completed task must not change completed_at.
  4. Reopening clears completed_at.
  5. Assigning an inactive user is a validation error.
  6. is_overdue is derived: due_date < today and status != done.
  7. Assignment sends an email through Celery, only after the transaction commits.

Structure (follow exactly)
- tasks/models.py, selectors.py, filters.py, services.py, serializers.py, views.py, urls.py
- Thin APIViews with @extend_schema. No ViewSet, no router, no repository layer.
- Services own rules; selectors own visibility; serializers own the contract.
- accounts/: JWT token/refresh, /me, active users list.

Constraints
- Do not invent abstractions (no use cases, DTOs, repositories, base service classes).
- Do not add dependencies beyond the list above.
- Every rule above needs a pytest test, including the edge cases.
- Settings must run with SQLite by default and PostgreSQL when DB_ENGINE=postgres.
- Do not write migrations by hand; use makemigrations.
- Do not add comments that restate the code.

Acceptance
- python manage.py check passes.
- pytest passes with coverage >= 80%.
- python manage.py spectacular --validate --fail-on-warn passes.
- ruff check and ruff format --check pass.
```

## Prompt de UI

```text
Build the React client with Vite + TypeScript + TanStack Query + React Hook Form.

Design constraints
- Use the design tokens of ballastlane.com: background #F4F6FA, ink #0B1220,
  blue #2B50BA, accent #FE5A0B, Space Grotesk for headings, Poppins for body,
  IBM Plex Mono for labels.
- Reuse the component patterns from ANA: button with cva variants, native <dialog>,
  loading and error components.
- Tailwind 4 with @theme inline mapping CSS variables to semantic colors.

Structure
- src/lib/api.ts is the only HTTP layer. It owns tokens and a single-flight refresh.
- src/features/tasks/{api,hooks,TaskBoard,TaskRow,TaskDialog}.tsx
- No global state library. Server state is TanStack Query; form state is React Hook Form.
- Loading, error, empty and success states must exist. No console warnings.
```

## Prompt do cliente HTMX

```text
Add a server-rendered client in a Django app named hypermedia, mounted at /app/.

Rules
- Reuse tasks.services, tasks.selectors and TaskCreateSerializer. Do not duplicate rules.
- Board page: filters (status, due date range, search, overdue), table of rows,
  create dialog, complete/reopen, delete with confirmation.
- HTMX for server state. Alpine only for local UI state (dialog open/closed).
- Create returns the reset form plus an out-of-band swap of the rows, and an
  HX-Trigger header to close the dialog.
- Invalid input returns 422 with the form partial; configure htmx responseHandling.
- CSRF via hx-headers on <body>. Foreign tasks return 404, never 403.
- Plain CSS with the same tokens as the React client; no build step for this app.
```

## O que o prompt não resolveu

O modelo acertou a estrutura e a maior parte das regras. O que exigiu revisão está em
[`02-review.md`](02-review.md): permissão morta, schema quebrado, throttle vazando entre
testes e uma divergência de status HTTP entre os dois clientes.
