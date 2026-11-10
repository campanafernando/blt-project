# Revisão do código gerado por IA

Registro do que a IA produziu, como o defeito foi detectado e o que mudou. Cada item
abaixo aconteceu neste repositório e foi encontrado por execução, não por leitura.

## 1. Classe de permissão morta

**Gerado:** `tasks/permissions.py` com `IsCreator`, uma classe de `BasePermission`.
**Problema:** nenhuma view usava. A checagem de exclusão era feita inline na view.
**Detecção:** `pytest --cov` mostrou 0% no arquivo; a leitura confirmou que não havia
import em lugar nenhum.
**Correção:** arquivo removido. Uma classe de permissão não usada sugere que a regra
existe em dois lugares — pior que não existir.
**Lição:** cobertura baixa em arquivo pequeno costuma ser código morto, não teste faltando.

## 2. Teste acessando estado interno do client

**Gerado:** `assigned_to=auth.handler._force_user` para montar o cenário de "responsável
não pode excluir".
**Problema:** `_force_user` é atributo privado do `APIClient`; o teste passava por acidente
e quebraria em qualquer refatoração.
**Correção:** o teste recebe a fixture `user` e usa `assigned_to=user`.
**Lição:** se o teste precisa de um underscore, o cenário está mal montado.

## 3. Schema OpenAPI inválido

**Gerado:** `parameters=[TaskFilter]` em uma `APIView`, e `MeApi`/`UserListApi` sem
`@extend_schema`.
**Problema:** `spectacular --validate --fail-on-warn` falhou com "could not resolve
parameter annotation" e "unable to guess serializer". O README prometia `/api/docs/`,
então isso quebrava uma entrega, não um detalhe.
**Correção:** parâmetros declarados com `OpenApiParameter` (status, datas, assigned_to,
overdue, search, page, page_size) e `@extend_schema(responses=...)` nas duas views de conta.
**Lição:** schema é teste. Se não roda no CI, ele apodrece.

## 4. Throttle vazando entre testes

**Gerado:** login com `throttle_scope = "login"` (10/min) e cache `LocMemCache`.
**Problema:** a suíte fazia login em quase todos os testes; a partir do décimo, os
requests viravam 429 e 15 testes falharam em cascata. O erro parecia de autenticação.
**Detecção:** a mensagem era `assert 429 == 200` na fixture de login.
**Correção:** `cache.clear()` antes e depois de cada teste, em fixture autouse.
**Lição:** throttle é estado global. Teste que autentica precisa limpar cache.

## 5. 403 vs 404 entre clientes

**Gerado:** no HTMX, exclusão de tarefa de outro usuário retornava 403.
**Problema:** a API responde 404 para não revelar a existência do recurso. O cliente
HTMX fazia diferente para a mesma regra.
**Correção:** o teste foi ajustado para 404 e o comportamento documentado. A view usa o
mesmo selector de escopo; a diferença era só a expectativa.
**Lição:** dois clientes sobre a mesma regra precisam de teste de contrato comparando
status, não só o caminho feliz.

## 6. Asserção em mensagem de validação do DRF

**Gerado:** teste esperando "não pode ficar em branco" no HTML.
**Problema:** `allow_blank=False` do campo dispara antes do `validate_title`, com outra
mensagem. O teste falhou mesmo com a resposta correta (422 + form).
**Correção:** assert na estrutura (`id="task-form"` e status 422), não no texto.
**Lição:** teste de mensagem é teste de tradução. Teste o contrato.

## 7. Cobertura inicial de 83%, não 97%

**Gerado:** testes cobrindo o caminho felizes das views.
**Problema:** `seed_demo` e o digest do Celery ficaram em 0% e 55%; o requisito era 80%,
mas o número escondia buracos reais.
**Correção:** teste do seed idempotente e do digest (uma tarefa, uma concluída, uma sem
responsável), além dos testes de borda de serviço.
**Lição:** cobertura é pista, não meta. O que importa é a borda que ninguém escreveu.

## 8. MinIO sem imagem publicada

**Gerado:** `image: minio/minio:latest` no compose.
**Problema:** o repositório oficial não existe mais; o `docker compose up` falharia.
**Correção:** build da release fixada a partir do código, como no ANA, e profile
`storage` para não encarecer o caminho principal.
**Lição:** infraestrutura gerada por IA assume que a imagem existe. Valide com
`docker compose build`, não com leitura.

## 9. Versões assumidas, não verificadas

**Gerado:** Django 5.2 LTS por hábito.
**Decisão:** subir para Django 6.0 exige conferir DRF, SimpleJWT, spectacular e
django-filter. A verificação foi instalar e rodar a suíte em Python 3.12 — passou.
**Lição:** "compatível" é resultado de execução, não de memória do modelo.

## O que a IA fez bem

- Estrutura de camadas consistente com o padrão que eu já uso (view → service → selector).
- Configuração de JWT, paginação e throttling sem inventar biblioteca.
- Testes de borda quando o prompt listava a borda explicitamente.
- Formulários e componentes React sem warning de console.

O padrão: **quanto mais explícito o critério de aceite, melhor a saída**. O que não estava
no prompt — status HTTP entre clientes, cache global, imagem de container — foi
exatamente o que quebrou.
