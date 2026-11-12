#!/bin/bash
# Rotate the shared password (seeded users and Gitea accounts) and the Django signing key.
#   make password                      asks for the new password (nothing is echoed)
#   BLT_PASSWORD=... make password     non-interactive
# The new Django key invalidates every session and token issued with the old password.
# Nothing is printed except what was done; the password is only written to secrets/blt_password.
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ -z "${BLT_PASSWORD:-}" ]]; then
  read -rsp "New shared password: " BLT_PASSWORD; echo
  read -rsp "Repeat it: " again; echo
  [[ "$BLT_PASSWORD" == "$again" ]] || { echo "The passwords differ." >&2; exit 1; }
fi
[[ ${#BLT_PASSWORD} -ge 6 ]] || { echo "Use at least 6 characters (Gitea's local minimum)." >&2; exit 1; }

mkdir -p secrets && chmod 700 secrets
# Written in place (">") so containers that already mounted the file see the new value.
printf '%s' "$BLT_PASSWORD" > secrets/blt_password
chmod 644 secrets/blt_password
openssl rand -hex 32 | tr -d '\n' > secrets/django_secret_key
chmod 644 secrets/django_secret_key
echo "Updated secrets/blt_password and secrets/django_secret_key."

COMPOSE="${COMPOSE:-docker compose -f infra/compose.yaml --env-file .env}"
if $COMPOSE ps --status running --services 2>/dev/null | grep -q '^api$'; then
  # Recreating the API runs the seed, which sets the new password on the BLT users.
  $COMPOSE up -d --force-recreate api worker beat >/dev/null 2>&1
  echo "Recreated api, worker and beat: BLT users now use the new password, old sessions are void."
  # Gitea's bootstrap resets the password of blt, ballast and lane every time it starts.
  $COMPOSE up -d --force-recreate gitea >/dev/null 2>&1
  echo "Recreated gitea: its accounts (blt, ballast, lane) now use the new password."
else
  echo "The stack is not running: the new password applies on the next 'make up' (or 'make seed')."
fi
