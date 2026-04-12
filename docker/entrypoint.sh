#!/bin/sh
# acmed container entrypoint.
# Usage: executed automatically as container ENTRYPOINT.
# Author: Ruslan Ovsyannikov <rovsyannikov@gmail.com>
# License: MIT

set -eu

TOKEN_FILE="${ACMED_TOKEN_ADMIN_FILE:-/run/secrets/acmed_token_admin}"

if [ -z "${ACMED_TOKEN_ADMIN:-}" ]; then
  if [ ! -r "$TOKEN_FILE" ]; then
    echo "acmed-entrypoint: missing admin token (set ACMED_TOKEN_ADMIN or mount readable $TOKEN_FILE)" >&2
    exit 2
  fi
  ACMED_TOKEN_ADMIN="$(tr -d '\r\n' < "$TOKEN_FILE")"
  if [ -z "$ACMED_TOKEN_ADMIN" ]; then
    echo "acmed-entrypoint: admin token file is empty: $TOKEN_FILE" >&2
    exit 2
  fi
  export ACMED_TOKEN_ADMIN
fi

exec python -m acmed.main /app/config/config.yml
