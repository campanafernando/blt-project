#!/bin/sh
set -e

if [ "${RUN_MIGRATIONS:-0}" = "1" ]; then
  python manage.py migrate --noinput
  python manage.py collectstatic --noinput
  if [ "${SEED_DATA:-0}" = "1" ]; then
    python manage.py seed
  fi
fi

# One image, several processes. Compose passes a command, so SERVICE_ROLE stays empty there.
# Railway deploys every service of this directory with the same settings, so the role comes
# from a variable instead.
case "${SERVICE_ROLE:-}" in
  "")
    exec "$@"
    ;;
  api)
    exec gunicorn config.wsgi:application --bind "[::]:${PORT:-8000}" \
      --workers "${WEB_CONCURRENCY:-3}" --timeout 60
    ;;
  worker)
    exec celery -A config worker -l info --concurrency "${CELERY_CONCURRENCY:-2}"
    ;;
  beat)
    exec celery -A config beat -l info --schedule=/tmp/celerybeat-schedule
    ;;
  seed)
    # Gitea answers a few seconds before its bootstrap has created the accounts, and the issues are
    # assigned to them: wait for the last one, then retry in case Gitea is still starting.
    attempt=1
    until curl -fsS "${GITEA_API_URL}/users/lane" > /dev/null 2>&1; do
      [ "$attempt" -gt 60 ] && { echo "Gitea accounts did not appear" >&2; exit 1; }
      attempt=$((attempt + 1))
      sleep 5
    done
    attempt=1
    while [ "$attempt" -le 60 ]; do
      if python manage.py gitea_bootstrap; then
        exit 0
      fi
      echo "gitea_bootstrap failed (attempt $attempt); retrying in 10 s"
      attempt=$((attempt + 1))
      sleep 10
    done
    exit 1
    ;;
  *)
    echo "Unknown SERVICE_ROLE: ${SERVICE_ROLE}" >&2
    exit 2
    ;;
esac
