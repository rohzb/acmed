#!/usr/bin/env sh
#
# Run end-to-end ACME chain smoke tests against the Pebble test stack.
#
# Usage:
#   /opt/chain-tests/chain-runner.sh
#
# Author: Ruslan Ovsyannikov <rovsyannikov@gmail.com>
# License: MIT
#

set -eu

ACMED_DIRECTORY_URL="${ACMED_DIRECTORY_URL:-http://acmed:8443/acme/directory}"
ACMED_ADMIN_API_URL="${ACMED_ADMIN_API_URL:-http://acmed:8443/api/v1/admin/orders}"
ACMED_ADMIN_TOKEN="${ACMED_ADMIN_TOKEN:-test-admin-token}"
PEBBLE_DIRECTORY_URL="${PEBBLE_DIRECTORY_URL:-https://pebble:14000/dir}"
PEBBLE_MANAGEMENT_URL="${PEBBLE_MANAGEMENT_URL:-https://pebble:15000}"
CHAIN_DEBUG="${CHAIN_DEBUG:-0}"
CHAIN_SUMMARY_FILE="${CHAIN_SUMMARY_FILE:-/tmp/chain-summary.txt}"
CHAIN_SUMMARY_JSON="${CHAIN_SUMMARY_JSON:-/tmp/chain-summary.json}"
CHAIN_STEP_RESULTS_FILE="${CHAIN_STEP_RESULTS_FILE:-/tmp/chain-step-results.tsv}"

if [ "$CHAIN_DEBUG" = "1" ]; then
  set -x
fi

STEP_NAME="initialization"
FAILED_STEP=""
FAILED_CODE=0
TOTAL_STEPS=0
PASSED_STEPS=0
: > "$CHAIN_STEP_RESULTS_FILE"

CERTBOT_ACMED_FULLCHAIN="/tmp/certbot-acmed/config/live/host1.lab.example.org/fullchain.pem"
ACMESH_ACMED_FULLCHAIN="/tmp/acmesh-acmed/certs/host2.lab.example.org_ecc/fullchain.cer"
CERTBOT_PEBBLE_FULLCHAIN="/tmp/certbot-pebble/config/live/pebble-certbot.lab.example.org/fullchain.pem"
ACMESH_PEBBLE_FULLCHAIN="/tmp/acmesh-pebble/certs/pebble-acmesh.lab.example.org_ecc/fullchain.cer"

write_step_result() {
  status="$1"
  name="$2"
  duration="$3"
  detail="$4"
  printf '%s|%s|%s|%s\n' "$status" "$name" "$duration" "$detail" >> "$CHAIN_STEP_RESULTS_FILE"
}

run_step() {
  _chain_step_name="$1"
  shift
  STEP_NAME="$_chain_step_name"
  TOTAL_STEPS=$((TOTAL_STEPS + 1))
  _chain_start_ts="$(date +%s)"
  echo "[step] start: ${_chain_step_name}"
  set +e
  "$@"
  _chain_rc="$?"
  set -e
  _chain_end_ts="$(date +%s)"
  _chain_duration="$((_chain_end_ts - _chain_start_ts))"
  if [ "$_chain_rc" -eq 0 ]; then
    PASSED_STEPS=$((PASSED_STEPS + 1))
    write_step_result "PASS" "$_chain_step_name" "$_chain_duration" ""
    echo "[step] pass: ${_chain_step_name} (${_chain_duration}s)"
    return 0
  fi

  FAILED_STEP="$_chain_step_name"
  FAILED_CODE="$_chain_rc"
  write_step_result "FAIL" "$_chain_step_name" "$_chain_duration" "rc=${_chain_rc}"
  echo "[step] fail: ${_chain_step_name} (${_chain_duration}s, rc=${_chain_rc})" >&2
  return "$_chain_rc"
}

print_summary() {
  exit_code="$1"
  overall="PASS"
  if [ "$exit_code" -ne 0 ] || [ -n "$FAILED_STEP" ]; then
    overall="FAIL"
  fi

  _summary_text="$(
  {
    echo "=== Pebble Chain Test Summary ==="
    echo "overall: ${overall}"
    echo "exit_code: ${exit_code}"
    echo "passed_steps: ${PASSED_STEPS}/${TOTAL_STEPS}"
    if [ "$overall" = "FAIL" ]; then
      echo "failed_step: ${FAILED_STEP}"
      echo "failed_rc: ${FAILED_CODE}"
    fi
    echo "summary_generated_at: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "---- step results ----"
    while IFS='|' read -r status name duration detail; do
      [ -n "$status" ] || continue
      if [ -n "$detail" ]; then
        echo "${status} ${name} (${duration}s) ${detail}"
      else
        echo "${status} ${name} (${duration}s)"
      fi
    done < "$CHAIN_STEP_RESULTS_FILE"
    echo "---- key artifacts ----"
    for p in \
      "$CERTBOT_ACMED_FULLCHAIN" \
      "$ACMESH_ACMED_FULLCHAIN" \
      "$CERTBOT_PEBBLE_FULLCHAIN" \
      "$ACMESH_PEBBLE_FULLCHAIN"; do
      if [ -f "$p" ]; then
        echo "present: $p"
      else
        echo "missing: $p"
      fi
    done
  })"
  printf '%s\n' "$_summary_text" | tee "$CHAIN_SUMMARY_FILE"

  OVERALL="$overall" \
  EXIT_CODE="$exit_code" \
  PASSED_STEPS="$PASSED_STEPS" \
  TOTAL_STEPS="$TOTAL_STEPS" \
  FAILED_STEP="$FAILED_STEP" \
  FAILED_CODE="$FAILED_CODE" \
  CHAIN_STEP_RESULTS_FILE="$CHAIN_STEP_RESULTS_FILE" \
  CHAIN_SUMMARY_JSON="$CHAIN_SUMMARY_JSON" \
  python - <<'PY'
import json
import os
from pathlib import Path

results = []
for raw in Path(os.environ["CHAIN_STEP_RESULTS_FILE"]).read_text(encoding="utf-8").splitlines():
    if not raw.strip():
        continue
    status, name, duration, detail = raw.split("|", 3)
    item = {
        "status": status,
        "name": name,
        "duration_seconds": int(duration),
    }
    if detail:
        item["detail"] = detail
    results.append(item)

payload = {
    "overall": os.environ["OVERALL"],
    "exit_code": int(os.environ["EXIT_CODE"]),
    "passed_steps": int(os.environ["PASSED_STEPS"]),
    "total_steps": int(os.environ["TOTAL_STEPS"]),
    "failed_step": os.environ["FAILED_STEP"] or None,
    "failed_rc": int(os.environ["FAILED_CODE"]) if os.environ["FAILED_STEP"] else None,
    "steps": results,
}
Path(os.environ["CHAIN_SUMMARY_JSON"]).write_text(
    json.dumps(payload, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
PY
  echo "[summary] json: ${CHAIN_SUMMARY_JSON}"
}

dump_debug_bundle() {
  echo "[debug] failure detected in step: ${STEP_NAME}" >&2
  echo "[debug] collecting local debug bundle" >&2

  echo "[debug] acmed directory response:" >&2
  curl -fsS "$ACMED_DIRECTORY_URL" 2>&1 || true
  echo >&2

  echo "[debug] pebble directory response:" >&2
  curl -fsS -k "$PEBBLE_DIRECTORY_URL" 2>&1 || true
  echo >&2

  echo "[debug] pebble management roots/0 response header:" >&2
  curl -fsS -k -I "${PEBBLE_MANAGEMENT_URL}/roots/0" 2>&1 || true
  echo >&2

  if [ -f /tmp/certbot-acmed/logs/letsencrypt.log ]; then
    echo "[debug] tail certbot->acmed log:" >&2
    tail -n 120 /tmp/certbot-acmed/logs/letsencrypt.log >&2 || true
  fi
  if [ -f /tmp/certbot-pebble/logs/letsencrypt.log ]; then
    echo "[debug] tail certbot->pebble log:" >&2
    tail -n 120 /tmp/certbot-pebble/logs/letsencrypt.log >&2 || true
  fi

  if [ -d /tmp/acmesh-acmed ]; then
    echo "[debug] acme.sh->acmed files:" >&2
    find /tmp/acmesh-acmed -maxdepth 4 -type f | sort >&2 || true
  fi
  if [ -d /tmp/acmesh-pebble ]; then
    echo "[debug] acme.sh->pebble files:" >&2
    find /tmp/acmesh-pebble -maxdepth 4 -type f | sort >&2 || true
  fi

  if [ -d /acmed-data/orders ]; then
    echo "[debug] /acmed-data/orders files:" >&2
    find /acmed-data/orders -maxdepth 3 -type f | sort >&2 || true
  fi

  echo "[debug] acmed admin orders snapshot:" >&2
  curl -fsS -H "Authorization: Bearer ${ACMED_ADMIN_TOKEN}" "${ACMED_ADMIN_API_URL}?limit=50" 2>&1 || true
  echo >&2
}

on_exit() {
  code="$1"
  if [ "$code" -ne 0 ]; then
    dump_debug_bundle
  fi
  print_summary "$code"
}

trap 'on_exit $?' EXIT

wait_for_url() {
  url="$1"
  insecure="${2:-false}"
  _chain_wait_name="${3:-endpoint}"
  timeout="${4:-120}"
  elapsed=0

  while [ "$elapsed" -lt "$timeout" ]; do
    echo "[wait] checking ${_chain_wait_name}: ${url} (${elapsed}s/${timeout}s)"
    if [ "$insecure" = "true" ]; then
      if curl -fsS -k "$url" >/dev/null 2>&1; then
        echo "[wait] ready: ${_chain_wait_name}"
        return 0
      fi
    else
      if curl -fsS "$url" >/dev/null 2>&1; then
        echo "[wait] ready: ${_chain_wait_name}"
        return 0
      fi
    fi
    sleep 2
    elapsed=$((elapsed + 2))
  done

  echo "[error] timed out waiting for ${_chain_wait_name}: $url" >&2
  return 1
}

wait_for_services() {
  wait_for_url "$ACMED_DIRECTORY_URL" false "acmed directory" 180
  wait_for_url "$PEBBLE_DIRECTORY_URL" true "pebble directory" 180
  wait_for_url "$PEBBLE_MANAGEMENT_URL/roots/0" true "pebble management root endpoint" 180
}

verify_pem_cert() {
  cert_path="$1"
  expected_dns="$2"
  label="$3"

  test -s "$cert_path" || {
    echo "[error] missing or empty certificate: $cert_path" >&2
    return 1
  }
  openssl x509 -in "$cert_path" -noout >/dev/null || {
    echo "[error] openssl failed to parse certificate: $cert_path" >&2
    return 1
  }
  openssl x509 -in "$cert_path" -noout -text | grep -F "DNS:${expected_dns}" >/dev/null || {
    echo "[error] expected SAN DNS:${expected_dns} not found in ${cert_path}" >&2
    return 1
  }
  subject="$(openssl x509 -in "$cert_path" -noout -subject 2>/dev/null || true)"
  issuer="$(openssl x509 -in "$cert_path" -noout -issuer 2>/dev/null || true)"
  echo "[check] ${label} subject: ${subject}"
  echo "[check] ${label} issuer: ${issuer}"
}

run_certbot_against_acmed() {
  cert_root="/tmp/certbot-acmed"
  mkdir -p "$cert_root/config" "$cert_root/work" "$cert_root/logs"

  timeout 300 certbot certonly \
    --standalone \
    --preferred-challenges http \
    --http-01-port 5002 \
    --server "$ACMED_DIRECTORY_URL" \
    --no-verify-ssl \
    --agree-tos \
    --register-unsafely-without-email \
    --config-dir "$cert_root/config" \
    --work-dir "$cert_root/work" \
    --logs-dir "$cert_root/logs" \
    -d host1.lab.example.org

  test -f "$CERTBOT_ACMED_FULLCHAIN" || return 1
}

run_acmesh_against_acmed() {
  acme_home="/tmp/acmesh-acmed/home"
  acme_config="/tmp/acmesh-acmed/config"
  acme_certs="/tmp/acmesh-acmed/certs"
  mkdir -p "$acme_home" "$acme_config" "$acme_certs"

  timeout 180 /usr/local/bin/acme.sh \
    --home "$acme_home" \
    --config-home "$acme_config" \
    --cert-home "$acme_certs" \
    --server "$ACMED_DIRECTORY_URL" \
    --insecure \
    --register-account \
    -m chain-test@example.invalid || true

  timeout 300 /usr/local/bin/acme.sh \
    --home "$acme_home" \
    --config-home "$acme_config" \
    --cert-home "$acme_certs" \
    --server "$ACMED_DIRECTORY_URL" \
    --insecure \
    --issue \
    --standalone \
    --httpport 5002 \
    -d host2.lab.example.org

  test -f "$ACMESH_ACMED_FULLCHAIN" || return 1
}

verify_acmed_orders() {
  response_file="/tmp/acmed-orders.json"
  curl -fsS \
    -H "Authorization: Bearer ${ACMED_ADMIN_TOKEN}" \
    "$ACMED_ADMIN_API_URL?limit=50" \
    > "$response_file"

  python - <<'PY'
import json
from pathlib import Path

payload = json.loads(Path("/tmp/acmed-orders.json").read_text(encoding="utf-8"))
orders = payload.get("orders", [])
if len(orders) < 2:
    raise SystemExit("expected at least 2 admin orders")

issued = [item for item in orders if item.get("status") == "issued"]
if len(issued) < 2:
    raise SystemExit("expected at least 2 issued orders from acmed flow")

names = set()
for item in issued:
    for dns_name in item.get("dns_names", []):
        names.add(str(dns_name))
missing = {"host1.lab.example.org", "host2.lab.example.org"} - names
if missing:
    raise SystemExit(f"issued orders missing expected domains: {sorted(missing)}")

print("[ok] acmed admin orders include issued results for expected domains")
PY
}

verify_acmed_artifact_contents() {
  response_file="/tmp/acmed-orders.json"
  curl -fsS \
    -H "Authorization: Bearer ${ACMED_ADMIN_TOKEN}" \
    "$ACMED_ADMIN_API_URL?limit=50" \
    > "$response_file"

  python - <<'PY'
import json
from pathlib import Path
import subprocess
import sys

orders = json.loads(Path("/tmp/acmed-orders.json").read_text(encoding="utf-8")).get("orders", [])
targets = {
    "host1.lab.example.org": None,
    "host2.lab.example.org": None,
}
for item in orders:
    if item.get("status") != "issued":
        continue
    names = set(item.get("dns_names") or [])
    for target in list(targets.keys()):
        if target in names and targets[target] is None:
            targets[target] = item.get("id")

missing_targets = [name for name, oid in targets.items() if not oid]
if missing_targets:
    raise SystemExit(f"missing issued orders for expected domains: {missing_targets}")

for domain, order_id in targets.items():
    root = Path("/acmed-data/orders") / order_id
    cert = root / "certificate.pem"
    fullchain = root / "fullchain.pem"
    key = root / "private.key"
    for p in (cert, fullchain, key):
        if not p.exists():
            raise SystemExit(f"missing artifact for {domain}: {p}")

    fullchain_blocks = fullchain.read_text(encoding="utf-8").count("BEGIN CERTIFICATE")
    if fullchain_blocks < 2:
        raise SystemExit(f"fullchain for {domain} has fewer than 2 certificate blocks")

    cert_pub = subprocess.check_output(
        "openssl x509 -in '{}' -pubkey -noout | openssl pkey -pubin -outform der | openssl dgst -sha256".format(cert),
        shell=True,
        text=True,
    ).strip()
    key_pub = subprocess.check_output(
        "openssl pkey -in '{}' -pubout -outform der | openssl dgst -sha256".format(key),
        shell=True,
        text=True,
    ).strip()
    if cert_pub != key_pub:
        raise SystemExit(f"public key mismatch between certificate and private key for {domain}")

    check = subprocess.run(
        ["openssl", "x509", "-in", str(cert), "-checkend", "0", "-noout"],
        text=True,
        capture_output=True,
    )
    if check.returncode != 0:
        raise SystemExit(f"certificate not currently valid for {domain}: {check.stderr or check.stdout}")

print("[ok] acmed artifacts content validated (chain depth, key match, current validity)")
PY
}

verify_admin_rejects_bad_token() {
  code="$(curl -sS -o /tmp/admin-bad-token.json -w '%{http_code}' \
    -H 'Authorization: Bearer definitely-wrong-token' \
    "$ACMED_ADMIN_API_URL" || true)"
  if [ "$code" != "401" ] && [ "$code" != "403" ]; then
    echo "[error] expected 401/403 for bad admin token, got ${code}" >&2
    cat /tmp/admin-bad-token.json >&2 || true
    return 1
  fi
  echo "[check] admin endpoint rejects invalid bearer token with ${code}"
}

verify_policy_denies_nonmatching_domain() {
  cert_root="/tmp/certbot-acmed-denied"
  mkdir -p "$cert_root/config" "$cert_root/work" "$cert_root/logs"

  set +e
  timeout 120 certbot certonly \
    --standalone \
    --preferred-challenges http \
    --http-01-port 5003 \
    --server "$ACMED_DIRECTORY_URL" \
    --no-verify-ssl \
    --agree-tos \
    --register-unsafely-without-email \
    --config-dir "$cert_root/config" \
    --work-dir "$cert_root/work" \
    --logs-dir "$cert_root/logs" \
    -d denied.example.org >/tmp/certbot-denied.out 2>&1
  rc=$?
  set -e

  if [ "$rc" -eq 0 ]; then
    echo "[error] expected certbot order for denied.example.org to fail, but it succeeded" >&2
    cat /tmp/certbot-denied.out >&2 || true
    return 1
  fi
  if ! grep -Ei "unauthorized|denied|policy|rejected|access denied" /tmp/certbot-denied.out >/dev/null; then
    echo "[error] denied-domain run failed but output did not include clear denial markers" >&2
    cat /tmp/certbot-denied.out >&2 || true
    return 1
  fi
  echo "[check] policy denies non-matching domain requests as expected"
}

verify_malformed_acme_request_rejected() {
  code="$(curl -sS -o /tmp/acme-malformed.json -w '%{http_code}' \
    -H 'Content-Type: application/jose+json' \
    -X POST \
    --data '{}' \
    http://acmed:8443/acme/new-account || true)"
  if [ "$code" != "400" ]; then
    echo "[error] expected malformed ACME request to return 400, got ${code}" >&2
    cat /tmp/acme-malformed.json >&2 || true
    return 1
  fi
  if ! grep -F 'urn:ietf:params:acme:error:' /tmp/acme-malformed.json >/dev/null; then
    echo "[error] malformed ACME response missing RFC problem type" >&2
    cat /tmp/acme-malformed.json >&2 || true
    return 1
  fi
  echo "[check] malformed ACME request rejected with problem+json payload"
}

verify_acmed_artifacts_volume() {
  test -d /acmed-data/orders
  fullchain_count="$(find /acmed-data/orders -type f -name fullchain.pem | wc -l | tr -d ' ')"
  key_count="$(find /acmed-data/orders -type f -name private.key | wc -l | tr -d ' ')"
  if [ "${fullchain_count}" -lt 2 ]; then
    echo "expected at least 2 fullchain.pem artifacts, found ${fullchain_count}" >&2
    return 1
  fi
  if [ "${key_count}" -lt 2 ]; then
    echo "expected at least 2 private.key artifacts, found ${key_count}" >&2
    return 1
  fi
  echo "[check] acmed artifact volume includes expected certificate files"
}

verify_pebble_management_endpoints() {
  curl -fsS -k "${PEBBLE_MANAGEMENT_URL}/roots/0" -o /tmp/pebble-root.pem
  curl -fsS -k "${PEBBLE_MANAGEMENT_URL}/intermediates/0" -o /tmp/pebble-intermediate.pem
  openssl x509 -in /tmp/pebble-root.pem -noout -subject | grep -F "Pebble Root CA" >/dev/null
  openssl x509 -in /tmp/pebble-intermediate.pem -noout -subject | grep -F "Pebble Intermediate CA" >/dev/null
  echo "[check] pebble management endpoints returned parseable root/intermediate certs"
}

run_certbot_against_pebble() {
  cert_root="/tmp/certbot-pebble"
  mkdir -p "$cert_root/config" "$cert_root/work" "$cert_root/logs"

  timeout 300 certbot certonly \
    --standalone \
    --preferred-challenges http \
    --http-01-port 5002 \
    --server "$PEBBLE_DIRECTORY_URL" \
    --no-verify-ssl \
    --agree-tos \
    --register-unsafely-without-email \
    --config-dir "$cert_root/config" \
    --work-dir "$cert_root/work" \
    --logs-dir "$cert_root/logs" \
    -d pebble-certbot.lab.example.org

  test -f "$CERTBOT_PEBBLE_FULLCHAIN" || return 1
}

run_acmesh_against_pebble() {
  acme_home="/tmp/acmesh-pebble/home"
  acme_config="/tmp/acmesh-pebble/config"
  acme_certs="/tmp/acmesh-pebble/certs"
  mkdir -p "$acme_home" "$acme_config" "$acme_certs"

  timeout 180 /usr/local/bin/acme.sh \
    --home "$acme_home" \
    --config-home "$acme_config" \
    --cert-home "$acme_certs" \
    --server "$PEBBLE_DIRECTORY_URL" \
    --insecure \
    --register-account \
    -m pebble-chain@example.invalid || true

  timeout 300 /usr/local/bin/acme.sh \
    --home "$acme_home" \
    --config-home "$acme_config" \
    --cert-home "$acme_certs" \
    --server "$PEBBLE_DIRECTORY_URL" \
    --insecure \
    --issue \
    --standalone \
    --httpport 5002 \
    -d pebble-acmesh.lab.example.org

  test -f "$ACMESH_PEBBLE_FULLCHAIN" || return 1
}

echo "[info] waiting for acmed and pebble endpoints"
run_step "wait for services" wait_for_services || exit $?

run_step "certbot -> acmed issuance" run_certbot_against_acmed || exit $?
run_step "verify certbot -> acmed certificate" verify_pem_cert "$CERTBOT_ACMED_FULLCHAIN" "host1.lab.example.org" "certbot->acmed" || exit $?

run_step "acme.sh -> acmed issuance" run_acmesh_against_acmed || exit $?
run_step "verify acme.sh -> acmed certificate" verify_pem_cert "$ACMESH_ACMED_FULLCHAIN" "host2.lab.example.org" "acme.sh->acmed" || exit $?

run_step "verify acmed admin orders" verify_acmed_orders || exit $?
run_step "verify acmed artifact volume" verify_acmed_artifacts_volume || exit $?
run_step "verify acmed artifact content integrity" verify_acmed_artifact_contents || exit $?
run_step "verify admin rejects invalid token" verify_admin_rejects_bad_token || exit $?
run_step "verify policy denies non-matching domain" verify_policy_denies_nonmatching_domain || exit $?
run_step "verify malformed acme request rejected" verify_malformed_acme_request_rejected || exit $?

run_step "verify pebble management endpoints" verify_pebble_management_endpoints || exit $?

run_step "certbot -> pebble issuance" run_certbot_against_pebble || exit $?
run_step "verify certbot -> pebble certificate" verify_pem_cert "$CERTBOT_PEBBLE_FULLCHAIN" "pebble-certbot.lab.example.org" "certbot->pebble" || exit $?

run_step "acme.sh -> pebble issuance" run_acmesh_against_pebble || exit $?
run_step "verify acme.sh -> pebble certificate" verify_pem_cert "$ACMESH_PEBBLE_FULLCHAIN" "pebble-acmesh.lab.example.org" "acme.sh->pebble" || exit $?

echo "[done] pebble chain smoke tests passed"
