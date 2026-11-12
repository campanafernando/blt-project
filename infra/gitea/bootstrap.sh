#!/bin/sh
# Start Gitea through its own entrypoint, then create the accounts (idempotent: an existing account
# only gets its password reset). The password is BLT_PASSWORD (Railway) or the secret file Compose mounts;
# GITEA_USER and GITEA_EMAIL have defaults. Used by Compose and by Railway.
set -u

if [ -z "${BLT_PASSWORD:-}" ] && [ -r /run/secrets/blt_password ]; then
  BLT_PASSWORD=$(tr -d '\r\n' < /run/secrets/blt_password)
fi

/usr/bin/entrypoint "$@" &
gitea_pid=$!
trap 'kill -TERM "$gitea_pid" 2>/dev/null' TERM INT

if [ -z "${BLT_PASSWORD:-}" ]; then
  echo "bootstrap: no BLT_PASSWORD and no /run/secrets/blt_password, no account created" >&2
else
  port="${GITEA__server__HTTP_PORT:-3000}"
  tries=0
  until curl -fsS "http://127.0.0.1:${port}/api/healthz" >/dev/null 2>&1; do
    tries=$((tries + 1))
    [ "$tries" -gt 90 ] && { echo "bootstrap: Gitea did not become healthy" >&2; break; }
    sleep 2
  done

  # Gitea refuses to run as root; the image's "git" user owns /data.
  as_git() { su-exec git env GITEA_WORK_DIR=/data GITEA_CUSTOM=/data/gitea gitea "$@"; }

  ensure_account() {
    # $1 username, $2 e-mail. A fresh account must not be flagged "must change password",
    # or Gitea refuses its API until the web flow is completed.
    as_git admin user create --username "$1" --password "$BLT_PASSWORD" --email "$2" \
      --must-change-password=false >/dev/null 2>&1 \
      || as_git admin user change-password --username "$1" --password "$BLT_PASSWORD" \
        --must-change-password=false >/dev/null 2>&1
    echo "bootstrap: account $1 ready"
  }

  ensure_account "${GITEA_USER:-blt}" "${GITEA_EMAIL:-blt@mail.com}"
  for person in ballast lane; do
    ensure_account "$person" "$person@blt.local"
  done
fi

wait "$gitea_pid"
