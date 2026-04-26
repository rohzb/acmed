#!/usr/bin/env sh
# Start acmed with optional issuer addon combinations.
# Usage: ./docker/scripts/up-with-issuers.sh [acmesh|certbot|both|none]
# Author: Ruslan Ovsyannikov <rovsyannikov@gmail.com>
# License: MIT

set -eu

MODE="${1:-both}"

case "$MODE" in
  acmesh) ACMED_PLUGIN_DIRS="acmed-issuer-acmesh" ;;
  certbot) ACMED_PLUGIN_DIRS="acmed-issuer-certbot" ;;
  both) ACMED_PLUGIN_DIRS="acmed-issuer-acmesh,acmed-issuer-certbot" ;;
  none) ACMED_PLUGIN_DIRS="" ;;
  *)
    echo "usage: $0 [acmesh|certbot|both|none]" >&2
    exit 2
    ;;
esac

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
DOCKER_DIR="$REPO_ROOT/docker"
ENV_FILE="$DOCKER_DIR/.env"

read_env_var() {
  key="$1"
  awk -F= -v k="$key" '$1==k {print substr($0, index($0, "=")+1); exit}' "$ENV_FILE" 2>/dev/null || true
}

if [ ! -f "$ENV_FILE" ]; then
  cp "$DOCKER_DIR/.env.example" "$ENV_FILE"
  chmod 0600 "$ENV_FILE"
fi

ACMED_UID="$(grep '^ACMED_UID=' "$ENV_FILE" | cut -d= -f2 || true)"
ACMED_GID="$(grep '^ACMED_GID=' "$ENV_FILE" | cut -d= -f2 || true)"
ACMED_DATA_DIR="$(read_env_var ACMED_DATA_DIR)"
ACMED_ADMIN_TOKEN_FILE="$(read_env_var ACMED_ADMIN_TOKEN_FILE)"

if [ -z "$ACMED_UID" ] || [ -z "$ACMED_GID" ]; then
  ACMED_UID=10001
  ACMED_GID=10001
fi

if [ -n "$ACMED_DATA_DIR" ]; then
  export ACMED_DATA_DIR
fi
if [ -n "$ACMED_ADMIN_TOKEN_FILE" ]; then
  export ACMED_ADMIN_TOKEN_FILE
fi

"$DOCKER_DIR/scripts/setup-host-paths.sh" "$ACMED_UID" "$ACMED_GID"
"$DOCKER_DIR/scripts/generate-admin-token.sh"

cd "$REPO_ROOT"
ACMED_IMAGE_TARGET="runtime" ACMED_PLUGIN_DIRS="$ACMED_PLUGIN_DIRS" docker compose \
  -f docker/docker-compose.yml \
  -f docker/docker-compose.issuers.yml \
  --env-file docker/.env \
  up -d --build
