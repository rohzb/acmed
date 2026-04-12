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

The default image is minimal and does not include `acme.sh` or `certbot`.
When issuer CLIs are needed, start with:

```bash
./docker/scripts/up-with-issuers.sh both
```

Valid modes:

- `acmesh`: image target `runtime-acmesh` (`acme.sh` only)
- `certbot`: image target `runtime-certbot` (`certbot` only)
- `both`: image target `runtime-issuers` (`acme.sh` + `certbot`)

To use issuer-enabled config:

```bash
cp docker/config/config.issuers.example.yml docker/config/config.yml
./docker/scripts/up-with-issuers.sh both
```

This setup uses `development_mode: true` and `tls_enabled: false`, so it is for local testing only.
The default issuer is `mock`, and runtime state is stored in `docker/data`.

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
