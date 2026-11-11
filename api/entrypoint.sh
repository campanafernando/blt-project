#!/bin/sh
set -e

if [ "${RUN_MIGRATIONS:-0}" = "1" ]; then
  python manage.py migrate --noinput
  python manage.py collectstatic --noinput
  if [ "${SEED_DATA:-0}" = "1" ]; then
    python manage.py seed
  fi
fi

exec "$@"
