#!/usr/bin/env bash
# Create or update the hosted BLT on Railway: project, nine services, volume, domains, variables and
# the first deploys. Safe to run again: it skips what exists and re-applies variables and settings.
#
#   deploy/railway.sh            do it
#   deploy/railway.sh --dry-run  print what it would do
#
# Needs: the Railway CLI logged in (`railway login`), python3, and these files (git-ignored):
#   secrets/blt_password        the shared password of the seeded users, Gitea and Mailpit
#   secrets/opencode_api_key    the AI provider key (override with OPENCODE_API_KEY_FILE)
# Secrets reach Railway on stdin, never as arguments. Details: README, "Hosting on Railway".
set -euo pipefail

PROJECT="${RAILWAY_PROJECT_NAME:-blt}"
ENVIRONMENT="production"
KEY_FILE="${OPENCODE_API_KEY_FILE:-secrets/opencode_api_key}"
DRY=0
[ "${1:-}" = "--dry-run" ] && DRY=1

cd "$(dirname "${BASH_SOURCE[0]}")/.."
say() { printf '\n== %s\n' "$*"; }
run() {
  if [ "$DRY" = 1 ]; then
    printf '  [dry-run] %s\n' "$*"
    [ -t 0 ] || cat > /dev/null   # a secret piped in is read and dropped, never shown
  else
    "$@"
  fi
}
json() { python3 -c "import sys,json; d=json.load(sys.stdin); $1"; }

# ---- preflight
command -v railway >/dev/null || { echo "Install the Railway CLI first." >&2; exit 1; }
railway whoami >/dev/null 2>&1 || { echo "Run 'railway login' first." >&2; exit 1; }
[ -s secrets/blt_password ] || { echo "secrets/blt_password is missing (make env)." >&2; exit 1; }
[ -s "$KEY_FILE" ] || { echo "$KEY_FILE is missing: spec generation would be off." >&2; exit 1; }

# ---- project
say "Project $PROJECT"
if railway status --json 2>/dev/null | json "sys.exit(0 if d.get('name')=='$PROJECT' else 1)"; then
  echo "  linked"
elif railway link -p "$PROJECT" >/dev/null 2>&1; then
  echo "  linked to the existing project"
else
  run railway init -n "$PROJECT"
fi
status() { railway status --json 2>/dev/null; }
exists() { status | json "print('yes' if any(s['node']['serviceName']=='$1' for s in d['environments']['edges'][0]['node']['serviceInstances']['edges']) else 'no')"; }
env_id() { status | json "print(d['environments']['edges'][0]['node']['id'])"; }
service_id() { status | json "print(next(s['node']['serviceId'] for s in d['environments']['edges'][0]['node']['serviceInstances']['edges'] if s['node']['serviceName']=='$1'))"; }
var_names() { railway variables -s "$1" --json 2>/dev/null | json "print(' '.join(d))"; }
gql() { run railway api "$1" >/dev/null; }

# ---- services
say "Services"
[ "$(exists Postgres)" = yes ] || run railway add -d postgres
[ "$(exists Redis)" = yes ] || run railway add -d redis
for s in gitea mailpit api worker beat seed web; do
  [ "$(exists "$s")" = yes ] || run railway add -s "$s"
done

# ---- public domains (the API stays private behind nginx) and the Gitea volume
say "Domains and volume"
for pair in web:8080 gitea:3000 mailpit:8025; do
  svc=${pair%%:*}; port=${pair##*:}
  case " $(var_names "$svc") " in *" RAILWAY_PUBLIC_DOMAIN "*) ;; *) run railway domain -s "$svc" -p "$port" ;; esac
done
if ! railway volume list --json 2>/dev/null | json "sys.exit(0 if any(v.get('serviceName')=='gitea' for v in (d if isinstance(d,list) else d.get('volumes',[]))) else 1)"; then
  run railway service link gitea
  run railway volume add -m /data
fi

# ---- variables (non-secret values as arguments; secrets on stdin)
say "Variables"
set_vars() { local svc=$1; shift; run railway variable set -s "$svc" --skip-deploys "$@" >/dev/null; echo "  $svc: $# set"; }
DB=('DB_ENGINE=postgres' 'POSTGRES_DB=${{Postgres.PGDATABASE}}' 'POSTGRES_USER=${{Postgres.PGUSER}}' 'POSTGRES_HOST=${{Postgres.PGHOST}}' 'POSTGRES_PORT=${{Postgres.PGPORT}}' 'POSTGRES_PASSWORD=${{Postgres.PGPASSWORD}}')
MAIL=(EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend 'EMAIL_HOST=${{mailpit.RAILWAY_PRIVATE_DOMAIN}}' EMAIL_PORT=1025 'DEFAULT_FROM_EMAIL=BLT <no-reply@blt.local>')
# Not called HTTPS_PROXY: pip and curl read that name as a proxy address and the build breaks.
set_vars api SERVICE_ROLE=api PORT=8000 RUN_MIGRATIONS=1 SEED_DATA=1 DEBUG=false TRUST_FORWARDED_PROTO=true NUM_PROXIES=2 WEB_CONCURRENCY=2 \
  "${DB[@]}" 'REDIS_URL=${{Redis.REDIS_URL}}' CELERY_TASK_ALWAYS_EAGER=false "${MAIL[@]}" \
  OPENCODE_BASE_URL=https://opencode.ai/inference/go/openai/v1 OPENCODE_MODEL=deepseek-v4.1-flash OPENCODE_TIMEOUT=45 SPEC_MAX_INPUT_CHARS=12000 \
  'ALLOWED_HOSTS=${{web.RAILWAY_PUBLIC_DOMAIN}},${{api.RAILWAY_PRIVATE_DOMAIN}},healthcheck.railway.app' 'CSRF_TRUSTED_ORIGINS=https://${{web.RAILWAY_PUBLIC_DOMAIN}}' \
  'GITEA_API_URL=http://${{gitea.RAILWAY_PRIVATE_DOMAIN}}:3000/api/v1' 'GITEA_URL=https://${{gitea.RAILWAY_PUBLIC_DOMAIN}}' GITEA_USER=blt GITEA_REPO=blt/tasks
for s in worker beat; do
  set_vars "$s" "SERVICE_ROLE=$s" DEBUG=false "${DB[@]}" 'REDIS_URL=${{Redis.REDIS_URL}}' CELERY_TASK_ALWAYS_EAGER=false 'DJANGO_SECRET_KEY=${{api.DJANGO_SECRET_KEY}}' "${MAIL[@]}"
done
set_vars seed SERVICE_ROLE=seed DEBUG=false 'DJANGO_SECRET_KEY=${{api.DJANGO_SECRET_KEY}}' 'BLT_PASSWORD=${{api.BLT_PASSWORD}}' \
  'GITEA_API_URL=http://${{gitea.RAILWAY_PRIVATE_DOMAIN}}:3000/api/v1' 'GITEA_URL=https://${{gitea.RAILWAY_PUBLIC_DOMAIN}}' GITEA_USER=blt GITEA_REPO=blt/tasks
set_vars gitea PORT=3000 GITEA__database__DB_TYPE=sqlite3 'GITEA__server__ROOT_URL=https://${{gitea.RAILWAY_PUBLIC_DOMAIN}}/' 'GITEA__server__DOMAIN=${{gitea.RAILWAY_PUBLIC_DOMAIN}}' \
  GITEA__server__HTTP_PORT=3000 GITEA__server__DISABLE_SSH=true GITEA__security__INSTALL_LOCK=true GITEA__security__MIN_PASSWORD_LENGTH=6 \
  GITEA__service__DISABLE_REGISTRATION=true GITEA__repository__DEFAULT_BRANCH=main GITEA_USER=blt GITEA_EMAIL=blt@mail.com 'BLT_PASSWORD=${{api.BLT_PASSWORD}}'
set_vars mailpit PORT=8025 MP_UI_BIND_ADDR=0.0.0.0:8025 MP_SMTP_BIND_ADDR=0.0.0.0:1025 MP_MAX_MESSAGES=500
# web: the reference is read when the container starts, so web is deployed after api (see below).
set_vars web PORT=8080 'API_UPSTREAM=http://${{api.RAILWAY_PRIVATE_DOMAIN}}:8000'

say "Secrets (stdin)"
tr -d '\r\n' < secrets/blt_password | run railway variable set BLT_PASSWORD --stdin -s api --skip-deploys >/dev/null
printf 'blt:%s' "$(tr -d '\r\n' < secrets/blt_password)" | run railway variable set MP_UI_AUTH --stdin -s mailpit --skip-deploys >/dev/null
tr -d '\r\n' < "$KEY_FILE" | run railway variable set OPENCODE_API_KEY --stdin -s api --skip-deploys >/dev/null
# A new Django key only when there is none, so a re-run does not log everyone out.
case " $(var_names api) " in
  *" DJANGO_SECRET_KEY "*) echo "  DJANGO_SECRET_KEY kept" ;;
  *) openssl rand -base64 48 | tr -d '\n' | run railway variable set DJANGO_SECRET_KEY --stdin -s api --skip-deploys >/dev/null ;;
esac

# ---- service settings: the CLI cannot set these, the GraphQL API can
say "Service settings"
if [ "$DRY" = 0 ]; then
  E=$(env_id)
  gql "mutation { serviceInstanceUpdate(serviceId: \"$(service_id api)\", environmentId: \"$E\", input: { healthcheckPath: \"/api/schema/\", healthcheckTimeout: 180 }) }"
  gql "mutation { serviceInstanceUpdate(serviceId: \"$(service_id seed)\", environmentId: \"$E\", input: { restartPolicyType: NEVER }) }"
else
  echo "  [dry-run] api healthcheck /api/schema/, seed restartPolicyType NEVER"
fi
run railway service source connect --image axllent/mailpit:v1.33.1 -s mailpit >/dev/null

# ---- deploys: gitea and api first; web and the rest after api is up, so API_UPSTREAM resolves
say "Deploys"
up() { run railway up "$2" --path-as-root -s "$1" -e "$ENVIRONMENT" -d -m "deploy/railway.sh" | tail -1; }
up gitea infra/gitea
up api api
if [ "$DRY" = 0 ]; then
  echo "  waiting for api (migrations and seed run on start)..."
  for _ in $(seq 1 60); do
    st=$(railway service status --all 2>/dev/null | awk '$1=="api"{print $NF}')
    case "$st" in SUCCESS) break ;; FAILED|CRASHED) echo "api $st: railway service logs -s api" >&2; exit 1 ;; esac
    sleep 15
  done
fi
up web web
up worker api
up beat api
up seed api   # creates the Gitea repository and issues; retries until Gitea answers

say "Done"
for s in web gitea mailpit; do
  d=$(railway variables -s "$s" --json 2>/dev/null | json "print(d.get('RAILWAY_PUBLIC_DOMAIN',''))" 2>/dev/null || true)
  [ -n "$d" ] && printf '  %-8s https://%s\n' "$s" "$d"
done
echo "  Users: fernando, ballast, lane. Password: secrets/blt_password. Gitea login: blt@mail.com"
