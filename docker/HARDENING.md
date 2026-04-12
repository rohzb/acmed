# Docker Hardening Guide

This guide describes the hardened local runtime layout under `docker/`.

## Runtime Layout

- `docker/config/config.yml`: active service config (read-only mount)
- `docker/data/`: writable runtime state (SQLite + artifacts)
- `docker/data/orders/`: per-order artifact directory
- `docker/secrets/acmed_token_admin`: admin API token secret (Docker secret source)

The default image target is `runtime-base` (no issuer CLIs).
Optional targets are available when explicitly requested:

- `runtime-acmesh`
- `runtime-certbot`
- `runtime-issuers`

## Bootstrap

Run from repository root:

```bash
./docker/scripts/up.sh
```

This command:

1. Creates `docker/.env` from template if missing.
2. Prepares runtime directories and permissions.
3. Creates `docker/secrets/acmed_token_admin` if missing.
4. Starts `acmed` with Docker Compose.

## Manual Steps

```bash
cp docker/.env.example docker/.env
./docker/scripts/setup-host-paths.sh
./docker/scripts/generate-admin-token.sh
docker compose -f docker/docker-compose.yml --env-file docker/.env up -d --build
```

For issuer-enabled images:

```bash
./docker/scripts/up-with-issuers.sh both
```

## Token Rotation

```bash
./docker/scripts/generate-admin-token.sh --force
docker compose -f docker/docker-compose.yml --env-file docker/.env up -d
```

## Ownership and Permissions

- Container runs as `ACMED_UID:ACMED_GID` (defaults to `10001:10001`).
- `docker/data` and `docker/data/orders` should be writable by that UID/GID.
- `docker/secrets/acmed_token_admin` should be mode `0600`.
- `docker/.env` should be mode `0600`.

If your host uses different service UID/GID, update `docker/.env`:

```bash
ACMED_UID=<uid>
ACMED_GID=<gid>
```
