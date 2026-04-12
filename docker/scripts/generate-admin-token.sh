#!/usr/bin/env sh
# Generate or rotate Docker secret file for ACMED admin token.
# Usage:
#   ./docker/scripts/generate-admin-token.sh
#   ./docker/scripts/generate-admin-token.sh --force
# Optional:
#   ACMED_ENV_FILE=/path/to/.env ./docker/scripts/generate-admin-token.sh
# Author: Ruslan Ovsyannikov <rovsyannikov@gmail.com>
# License: MIT

set -eu

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
ENV_FILE="${ACMED_ENV_FILE:-$REPO_ROOT/docker/.env}"

if [ -f "$ENV_FILE" ]; then
  # shellcheck disable=SC1090
  set -a
  . "$ENV_FILE"
  set +a
fi

DOCKER_DIR="$REPO_ROOT/docker"
resolve_path() {
  case "$1" in
    /*) printf '%s\n' "$1" ;;
    *) printf '%s/%s\n' "$DOCKER_DIR" "$1" ;;
  esac
}

TOKEN_FILE_RAW="${ACMED_ADMIN_TOKEN_FILE:-./secrets/acmed_token_admin}"
TOKEN_FILE="$(resolve_path "$TOKEN_FILE_RAW")"
ACMED_UID="${ACMED_UID:-10001}"
ACMED_GID="${ACMED_GID:-10001}"
FORCE=0

if [ "${1:-}" = "--force" ]; then
  FORCE=1
fi

mkdir -p "$(dirname "$TOKEN_FILE")"

if [ -f "$TOKEN_FILE" ] && [ "$FORCE" -ne 1 ]; then
  echo "token already exists: $TOKEN_FILE (use --force to rotate)"
  exit 0
fi

if command -v openssl >/dev/null 2>&1; then
  TOKEN="$(openssl rand -hex 48)"
else
  TOKEN="$(python -c 'import secrets; print(secrets.token_hex(48))')"
fi

umask 177
printf '%s\n' "$TOKEN" > "$TOKEN_FILE"
chmod 0600 "$TOKEN_FILE"

if ! chown "$ACMED_UID:$ACMED_GID" "$TOKEN_FILE" 2>/dev/null; then
  echo "warning: could not chown token file to $ACMED_UID:$ACMED_GID" >&2
fi

echo "wrote admin token secret: $TOKEN_FILE"
