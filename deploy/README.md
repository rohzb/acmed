# Deployment Bundles

This repository includes both deployment styles that previously lived in separate wrapper directories:

- source-build presets: build local images from checked-out sources
- prebuilt-image presets: run published container images

## Compose presets

Source-build mode:

- `deploy/compose/compose.core-only.source.yaml`
- `deploy/compose/compose.core-acmesh.source.yaml`
- `deploy/compose/compose.core-certbot.source.yaml`
- `deploy/compose/compose.full.source.yaml`

Prebuilt-image mode:

- `deploy/compose/compose.core-only.image.yaml`
- `deploy/compose/compose.core-acmesh.image.yaml`
- `deploy/compose/compose.core-certbot.image.yaml`
- `deploy/compose/compose.full.image.yaml`

## Config files

- `deploy/config/config.remote.example.yml`: development-oriented remote-issuer config example
- `deploy/config/config.yml`: local copy used by `*.image.yaml` files (create from example)

## Quick start

Source-build full stack:

```bash
cd deploy/compose
mkdir -p runtime/core-data

docker compose -f compose.full.source.yaml up --build
```

Prebuilt-image full stack:

```bash
cd deploy/compose
cp ../config/config.remote.example.yml ../config/config.yml
mkdir -p runtime/core-data

ACMED_TOKEN_ADMIN='replace-me' \
ACMED_REMOTE_PLUGIN_TOKEN='replace-me' \
docker compose -f compose.full.image.yaml up
```

Health checks:

```bash
curl -s http://127.0.0.1:8443/healthz
curl -s http://127.0.0.1:8443/acme/directory
```
