# Decisões de arquitetura

Formato curto: contexto, decisão, consequência. O que foi descartado está no fim de cada
item, porque a pergunta de review quase sempre é "por que não X?".

## 1. Django 6.0 em vez de 5.2 LTS

**Contexto:** o alvo usa Django 6.x; meu histórico de produção é 5.2 LTS.
**Decisão:** 6.0, com Python 3.12, verificando DRF 3.18, SimpleJWT 5.5, spectacular 0.29
e django-filter 25 na prática (instalação + suíte + schema).
**Consequência:** alinhamento com o alvo e uso de template partials no cliente HTMX.
Risco: ecossistema de terceiros menos maduro; mitigado por pinos e CI.
**Descartado:** 5.2 LTS, mais seguro, mas não demonstra o stack pedido.

## 2. SQLite por padrão, PostgreSQL em Compose/CI

**Contexto:** o exercício aceita os dois; o revisor precisa rodar sem fricção.
**Decisão:** `DB_ENGINE=sqlite` por padrão; Compose e CI usam Postgres 16.
**Consequência:** `make setup && make test` funciona sem Docker. O risco é uma feature
depender de comportamento específico de Postgres e passar despercebida — por isso o CI
roda no Postgres.
**Descartado:** exigir Postgres sempre; mais fiel, pior para avaliação rápida.

## 3. `APIView` explícita, sem ViewSet

**Contexto:** o domínio tem seis operações com regras próprias (complete, reopen, assign).
**Decisão:** uma classe por operação, com `@extend_schema`.
**Consequência:** o mapa de endpoints é legível no arquivo; cada resposta tem status
explícito. Custo: mais classes que um ViewSet.
**Descartado:** `ModelViewSet` + `@action`; menos código, mas esconde transições e
dificulta explicar idempotência no review.

## 4. Serviço e selector em vez de repositório/use case

**Contexto:** "Clean Architecture" no enunciado costuma virar camada cerimonial.
**Decisão:** três camadas com responsabilidade real: view (HTTP), service (regra),
selector (consulta/escopo). Sem DTO, repositório ou interface abstrata.
**Consequência:** a regra existe uma vez e é testável sem HTTP. O que não existe não
precisa ser explicado.
**Descartado:** arquitetura hexagonal completa; mais camadas, nenhuma regra adicional.

## 5. JWT no `localStorage`

**Contexto:** API stateless + SPA sem backend-for-frontend.
**Decisão:** access e refresh em `localStorage`, refresh single-flight no `apiFetch`.
**Consequência:** simples e sem CSRF para a API; vulnerável a XSS. Em produção, cookie
`HttpOnly` + `SameSite` + CSRF, ou BFF.
**Descartado:** cookie de sessão para o React; exigiria CSRF em toda mutação e um proxy
de mesma origem, que o exercício não pede.

## 6. drf-spectacular em vez de drf-yasg

**Contexto:** o enunciado cita drf-yasg, que está sem manutenção e gera Swagger 2.
**Decisão:** drf-spectacular, OpenAPI 3, com `--validate --fail-on-warn` no `make check`.
**Consequência:** schema válido entra no CI; o cliente React poderia ser gerado a partir
dele. Custo: anotações explícitas em cada view.
**Descartado:** drf-yasg; compatível com o texto, pior decisão técnica.

## 7. Cliente HTMX na mesma base de código

**Contexto:** a vaga usa HTMX + Alpine como padrão SSR e React no legado.
**Decisão:** app `hypermedia` dentro do projeto Django, chamando os mesmos serviços.
**Consequência:** prova que a regra não está presa ao DRF. Um deploy serve os dois.
**Descartado:** projeto Django separado; duplicaria settings, migrações e regra.

## 8. `transaction.on_commit` para e-mail

**Contexto:** atribuir tarefa dispara notificação.
**Decisão:** agendar o Celery só depois do commit, com `on_commit`.
**Consequência:** nunca existe e-mail de tarefa que falhou ao salvar. Em teste, o callback
é capturado explicitamente.
**Descartado:** `.delay()` direto; mais simples, mas notifica antes de garantir o dado.

## 9. `is_overdue` derivado

**Contexto:** "atrasada" muda com o passar do dia.
**Decisão:** propriedade calculada e filtro SQL equivalente.
**Consequência:** nunca fica stale; custo desprezível no volume do domínio.
**Descartado:** campo booleano atualizado por job; exige job, sofre drift.

## 10. MinIO em profile

**Contexto:** imagens oficiais do MinIO não são mais publicadas; o build leva minutos.
**Decisão:** Dockerfile próprio com release fixada, atrás do profile `storage`.
**Consequência:** `make up` sobe em segundos com o essencial; storage é opcional e
documentado.
**Descartado:** MinIO no caminho padrão; encareceria a primeira execução do revisor.
