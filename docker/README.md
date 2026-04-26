# Docker Examples

This directory contains a local Docker setup for running `acmed` quickly.
For a focused hardening runbook, see [HARDENING.md](HARDENING.md).

The compose file runs one `acmed` service with persistent data under `docker/data`.
You choose one config profile, copy it to `docker/config/config.yml`, and start the service.
Admin token material is loaded from `docker/secrets/acmed_token_admin` (Docker secret mount), not from `docker/.env`.
The included profiles are:

- `config/config.allow-all.yml` for a permissive first run
- `config/config.source-subnet-local.yml` for local/private subnet pre-auth
- `config/config.trusted-bypass-local.yml` for development-only trusted bypass mode
- `config/config.issuers.example.yml` for acme.sh/certbot image targets

## Quick Start

Run these commands from the repository root (for example after `git clone https://github.com/rohzb/acmed.git` and `cd acmed`).

1. Copy env template:

   ```bash
   cp docker/.env.example docker/.env
   ```

2. (Optional) edit `docker/.env`:
   - set `ACMED_UID` / `ACMED_GID` if host ownership should differ from `10001:10001`
   - set `ACMED_PUBLISH_IP=0.0.0.0` for host-wide exposure (default) or `127.0.0.1` for loopback-only
   - set `ACMED_PUBLISH_PORT` to expose a different host port
   - set `ACMED_DATA_DIR` / `ACMED_ADMIN_TOKEN_FILE` to customize host storage paths

3. Choose a starter config profile and copy it to `config/config.yml` (or create your own `config/config.yml`):

   Option A (`allow_all`, easiest first run):

   ```bash
   cp docker/config/config.allow-all.yml docker/config/config.yml
   ```

   Option B (`source_subnet` pre-auth for local/private networks):

   ```bash
   cp docker/config/config.source-subnet-local.yml docker/config/config.yml
   ```

   Option C (`source_subnet` + trusted challenge bypass in development mode):

   ```bash
   cp docker/config/config.trusted-bypass-local.yml docker/config/config.yml
   ```

4. Bootstrap host paths, generate admin token secret, and start:

   ```bash
   ./docker/scripts/up.sh
   ```

   If you prefer manual start:

   ```bash
   ./docker/scripts/setup-host-paths.sh
   ./docker/scripts/generate-admin-token.sh
   docker compose -f docker/docker-compose.yml --env-file docker/.env up --build
   ```

5. Test health endpoint:

   ```bash
   curl -s http://127.0.0.1:8443/healthz
   ```

6. Get ACME directory:

   ```bash
   curl -s http://127.0.0.1:8443/acme/directory
   ```

## Optional Issuer Tooling Images

The default image includes only core `acmed`.
Issuer CLIs and extensions are added through selected plugin addons.
When issuer tooling is needed, start with:

```bash
./docker/scripts/up-with-issuers.sh both
```

Valid modes:

- `acmesh`: plugin addons `acmed-issuer-acmesh`
- `certbot`: plugin addons `acmed-issuer-certbot`
- `both`: plugin addons `acmed-issuer-acmesh,acmed-issuer-certbot`
- `none`: no external issuer addons

When `acmed-issuer-acmesh` is selected, build-time addon install includes
`acme.sh` and `dnsapi` hooks.

Issuer backends are plugin-based:

- `mock` is built into `acmed`
- `acme_sh` and `certbot` are loaded from installed Python entry-point plugins
  (`acmed.issuer_backends`) selected by `ACMED_PLUGIN_DIRS`

To use issuer-enabled config:

```bash
cp docker/config/config.issuers.example.yml docker/config/config.yml
./docker/scripts/up-with-issuers.sh both
```

This setup uses `development_mode: true` and `tls_enabled: false`, so it is for local testing only.
The default issuer is `mock`, and runtime state is stored in `docker/data`.

When building this Dockerfile from the monorepo app workspace, use build
context `apps/acmed/sources` and keep `acmed` plus any selected plugin addon
directories present:

- `acmed`

## Pebble Chain Smoke Tests

For deterministic local ACME integration checks, this repository includes a dedicated
test stack:

- `pebble`: ACME test CA
- `acmed`: runtime image with issuer tooling available
- `chain-tests`: client runner with `certbot` and `acme.sh`

The chain runner performs:

- `certbot -> acmed` issuance
- `acme.sh -> acmed` issuance
- admin-order verification from `acmed`
- `certbot -> pebble` issuance
- `acme.sh -> pebble` issuance

Run from repository root:

```bash
./docker/scripts/test-pebble-chain.sh
```

Debug-friendly modes:

```bash
# keep containers running after failure for manual inspection
CHAIN_KEEP_STACK=1 ./docker/scripts/test-pebble-chain.sh

# enable shell trace logs in the chain runner
CHAIN_DEBUG=1 ./docker/scripts/test-pebble-chain.sh

# run Pebble-side clients in strict TLS mode (no insecure client flags);
# chain runner builds a CA bundle from Pebble root/intermediate/WFE chain
CHAIN_STRICT_TLS=1 ./docker/scripts/test-pebble-chain.sh

# combine both for deep troubleshooting
CHAIN_DEBUG=1 CHAIN_KEEP_STACK=1 ./docker/scripts/test-pebble-chain.sh
```

The chain runner now emits a structured summary at the end of every run:

- overall status (`PASS`/`FAIL`)
- exit code
- per-step pass/fail results with durations
- failed step and rc (on failure)
- key artifact presence checks

By default the summary is written inside the test container to:

- `/tmp/chain-summary.txt`
- `/tmp/chain-summary.json`

and is also printed by the host wrapper from compose logs after each run.

Reproducibility defaults and overrides:

- Pebble image defaults to `ghcr.io/letsencrypt/pebble:latest` in `docker-compose.pebble-test.yml`.
- `acme.sh` defaults to `3.1.2` in Docker build args.
- override Pebble image (including digest-pinned form) with `PEBBLE_IMAGE`, for example:

  ```bash
  PEBBLE_IMAGE='ghcr.io/letsencrypt/pebble@sha256:<digest>' ./docker/scripts/test-pebble-chain.sh
  ```

- override acme.sh reference with `ACMESH_REF` when needed:

  ```bash
  ACMESH_REF='3.1.2' ./docker/scripts/test-pebble-chain.sh
  ```

Compose file and config used by this flow:

- `docker/docker-compose.pebble-test.yml`
- `docker/config/config.pebble-chain-test.yml`

Notes:

- this test profile is intentionally development-only (`trusted_bypass`, non-TLS `acmed`)
- `pebble` runs with `PEBBLE_VA_ALWAYS_VALID=1` for deterministic challenge behavior
- the `acmed` side of this stack uses the `mock` issuer profile to keep the broker path stable for smoke testing
- on failure the host wrapper prints compose status and recent logs automatically
- the client runner also emits a local debug bundle (endpoint probes, certbot log tails, acme.sh file listing, admin-order snapshot)
- extra checks include certificate parsing/SAN validation, Pebble management cert checks, and shared `acmed` artifact volume validation
- additional negative checks verify invalid admin tokens are rejected, out-of-policy domains are denied, and malformed ACME requests return ACME problem responses

## Container Hardening Defaults

The compose service applies baseline hardening for local development:

- Runs as non-root user by default (`ACMED_UID`/`ACMED_GID`).
- Uses a named volume (`acmed_data`) bound to `./data` for deterministic local storage.
- Supports customizable host paths via `.env` (`ACMED_DATA_DIR`, `ACMED_ADMIN_TOKEN_FILE`).
- Drops all Linux capabilities and enables `no-new-privileges`.
- Uses read-only root filesystem with writable mounts only where needed.
- Publishes container port `8443` on `${ACMED_PUBLISH_IP:-0.0.0.0}:${ACMED_PUBLISH_PORT:-8443}`.
- Adds a healthcheck, PID limit, and log rotation options.
- Loads the admin token from Docker secrets (`/run/secrets/acmed_token_admin`) via entrypoint.

## Helper Scripts

- `docker/scripts/setup-host-paths.sh`: create `docker/data` and `docker/secrets` with hardened modes and correct owner.
- `docker/scripts/generate-admin-token.sh`: generate or rotate `docker/secrets/acmed_token_admin`.
- `docker/scripts/up.sh`: one-shot bootstrap and `docker compose up -d --build`.
- `docker/scripts/up-with-issuers.sh`: bootstrap and start with optional issuer-enabled image targets.
