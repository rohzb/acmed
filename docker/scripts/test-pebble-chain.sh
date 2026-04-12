#!/usr/bin/env sh
#
# Run Pebble + acmed + client end-to-end chain smoke tests via Docker Compose.
#
# Usage:
#   ./docker/scripts/test-pebble-chain.sh
#
# Author: Ruslan Ovsyannikov <rovsyannikov@gmail.com>
# License: MIT
#

set -eu

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
COMPOSE_FILE="$REPO_ROOT/docker/docker-compose.pebble-test.yml"
KEEP_STACK="${CHAIN_KEEP_STACK:-0}"
DEBUG="${CHAIN_DEBUG:-0}"
RESULT=0

if ! command -v docker >/dev/null 2>&1; then
  echo "[error] docker command not found" >&2
  exit 127
fi

cleanup() {
  if [ "$RESULT" -ne 0 ]; then
    echo "[debug] chain test failed, compose service status:" >&2
    docker compose -f "$COMPOSE_FILE" ps >&2 || true
    echo "[debug] chain test failed, recent logs:" >&2
    docker compose -f "$COMPOSE_FILE" logs --tail=200 >&2 || true
  fi

  if [ "$KEEP_STACK" = "1" ]; then
    echo "[info] CHAIN_KEEP_STACK=1 set, leaving stack running for manual debugging." >&2
    echo "[info] inspect with: docker compose -f $COMPOSE_FILE ps" >&2
    echo "[info] logs with:    docker compose -f $COMPOSE_FILE logs -f" >&2
    return 0
  fi

  cd "$REPO_ROOT"
  docker compose -f "$COMPOSE_FILE" down -v --remove-orphans >/dev/null 2>&1 || true
}

trap cleanup EXIT INT TERM

cd "$REPO_ROOT"
if [ "$DEBUG" = "1" ]; then
  echo "[info] CHAIN_DEBUG=1 enabled, runner will print shell traces." >&2
fi
docker compose -f "$COMPOSE_FILE" up --build --abort-on-container-exit --exit-code-from chain-tests || RESULT=$?
echo "[info] chain summary (from chain-tests):"
docker compose -f "$COMPOSE_FILE" logs --no-color chain-tests 2>/dev/null | sed -n '/=== Pebble Chain Test Summary ===/,$p' || true
exit "$RESULT"
