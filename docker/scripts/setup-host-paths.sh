#!/usr/bin/env sh
# Prepare local Docker runtime directories with secure ownership and modes.
# Usage: ./docker/scripts/setup-host-paths.sh [acmed_uid] [acmed_gid]
# Optional:
#   ACMED_ENV_FILE=/path/to/.env ./docker/scripts/setup-host-paths.sh
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

DATA_DIR_RAW="${ACMED_DATA_DIR:-./data}"
TOKEN_FILE_RAW="${ACMED_ADMIN_TOKEN_FILE:-./secrets/acmed_token_admin}"
DATA_DIR="$(resolve_path "$DATA_DIR_RAW")"
ORDERS_DIR="$DATA_DIR/orders"
TOKEN_FILE="$(resolve_path "$TOKEN_FILE_RAW")"
SECRETS_DIR="$(dirname "$TOKEN_FILE")"

ACMED_UID="${1:-${ACMED_UID:-10001}}"
ACMED_GID="${2:-${ACMED_GID:-10001}}"

mkdir -p "$DATA_DIR" "$ORDERS_DIR" "$SECRETS_DIR"

if ! chown -R "$ACMED_UID:$ACMED_GID" "$DATA_DIR" 2>/dev/null; then
  echo "warning: could not chown $DATA_DIR to $ACMED_UID:$ACMED_GID (run with privileges if needed)" >&2
fi
chmod 0750 "$DATA_DIR"
chmod 0750 "$ORDERS_DIR"

if [ -f "$TOKEN_FILE" ]; then
  if ! chown "$ACMED_UID:$ACMED_GID" "$TOKEN_FILE" 2>/dev/null; then
    echo "warning: could not chown $TOKEN_FILE to $ACMED_UID:$ACMED_GID (run with privileges if needed)" >&2
  fi
  chmod 0600 "$TOKEN_FILE"
fi

chmod 0700 "$SECRETS_DIR"

printf 'prepared: %s (owner %s:%s, mode 750)\n' "$DATA_DIR" "$ACMED_UID" "$ACMED_GID"
printf 'prepared: %s (mode 750)\n' "$ORDERS_DIR"
printf 'prepared: %s (mode 700)\n' "$SECRETS_DIR"
