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
RESULTS_ROOT="${CHAIN_RESULTS_DIR:-$REPO_ROOT/docker/test-results/pebble-chain}"
RESULT=0
ARTIFACT_DIR=""

if ! command -v docker >/dev/null 2>&1; then
  echo "[error] docker command not found" >&2
  exit 127
fi

collect_chain_artifacts() {
  container_id="$(docker compose -f "$COMPOSE_FILE" ps -q chain-tests 2>/dev/null || true)"
  if [ -z "$container_id" ]; then
    return 0
  fi

  run_stamp="$(date -u +%Y%m%dT%H%M%SZ)"
  ARTIFACT_DIR="${RESULTS_ROOT}/${run_stamp}"
  mkdir -p "$ARTIFACT_DIR"

  docker cp "${container_id}:/tmp/chain-summary.txt" "${ARTIFACT_DIR}/chain-summary.txt" >/dev/null 2>&1 || true
  docker cp "${container_id}:/tmp/chain-summary.json" "${ARTIFACT_DIR}/chain-summary.json" >/dev/null 2>&1 || true
  docker cp "${container_id}:/tmp/chain-step-results.tsv" "${ARTIFACT_DIR}/chain-step-results.tsv" >/dev/null 2>&1 || true
  docker cp "${container_id}:/tmp/certbot-pebble/logs/letsencrypt.log" "${ARTIFACT_DIR}/certbot-pebble.log" >/dev/null 2>&1 || true
  docker cp "${container_id}:/tmp/certbot-acmed/logs/letsencrypt.log" "${ARTIFACT_DIR}/certbot-acmed.log" >/dev/null 2>&1 || true

  if [ -f "${ARTIFACT_DIR}/chain-summary.txt" ] || [ -f "${ARTIFACT_DIR}/chain-summary.json" ]; then
    echo "[info] saved chain artifacts to: ${ARTIFACT_DIR}"
  fi
}

cleanup() {
  collect_chain_artifacts

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
