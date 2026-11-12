#!/bin/sh
# Create ./secrets/* (git-ignored) and move any secret still sitting in .env into it.
# Idempotent: an existing, non-empty secret file is never overwritten. Never prints a value.
#   BLT_PASSWORD=...        sets the shared password for the seeded users and the Gitea accounts
#   OPENCODE_API_KEY=...    stores the AI provider key
set -eu

dir=secrets
mkdir -p "$dir"
chmod 700 "$dir"

legacy() { # value of KEY in .env, unless it is empty or a placeholder
  [ -f .env ] || return 0
  value=$(sed -n "s/^$1=//p" .env | head -1)
  case "$value" in "" | change-this* | django-insecure*) ;; *) printf '%s' "$value" ;; esac
}

put() { # put NAME VALUE
  file="$dir/$1"
  if [ -s "$file" ]; then return 0; fi
  printf '%s' "$2" > "$file"
  # 644 inside a 700 directory: containers run as other uids and must read the mount,
  # while other users of this machine cannot even enter the directory.
  chmod 644 "$file"
  echo "created $file"
}

random() { openssl rand -hex "$1"; }

put blt_password "${BLT_PASSWORD:-$(legacy GITEA_PASSWORD)}"
[ -s "$dir/blt_password" ] || put blt_password "$(random 12)"
put postgres_password "$(legacy POSTGRES_PASSWORD)"
[ -s "$dir/postgres_password" ] || put postgres_password "$(random 16)"
put django_secret_key "$(legacy SECRET_KEY)"
[ -s "$dir/django_secret_key" ] || put django_secret_key "$(random 32)"
put minio_root_password "$(legacy S3_SECRET_KEY)"
[ -s "$dir/minio_root_password" ] || put minio_root_password "$(random 16)"
put minio_ro_secret "$(legacy MINIO_RO_SECRET_KEY)"
[ -s "$dir/minio_ro_secret" ] || put minio_ro_secret "$(random 16)"
# These two may legitimately be empty: AI off, and no SMTP login.
[ -f "$dir/opencode_api_key" ] || { printf '%s' "${OPENCODE_API_KEY:-$(legacy OPENCODE_API_KEY)}" > "$dir/opencode_api_key"; chmod 644 "$dir/opencode_api_key"; echo "created $dir/opencode_api_key"; }
[ -f "$dir/email_host_password" ] || { printf '%s' "$(legacy EMAIL_HOST_PASSWORD)" > "$dir/email_host_password"; chmod 644 "$dir/email_host_password"; echo "created $dir/email_host_password"; }

# Remove the secrets (and stale duplicates) from .env: it only keeps plain configuration.
if [ -f .env ]; then
  for key in POSTGRES_PASSWORD SECRET_KEY S3_SECRET_KEY MINIO_RO_SECRET_KEY GITEA_PASSWORD \
             OPENCODE_API_KEY EMAIL_HOST_PASSWORD GITEA_TOKEN \
             BLT_PG_HOST BLT_PG_PORT BLT_PG_NAME BLT_PG_USER BLT_PG_PASSWORD \
             MINIO_ENDPOINT MINIO_ACCESS_KEY MINIO_SECRET_KEY MINIO_BUCKET; do
    sed -i "/^$key=/d" .env
  done
  chmod 600 .env
fi
