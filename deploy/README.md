# Deployment Bundles

This repository includes both deployment styles that previously lived in separate wrapper directories:

- source-build presets: build local images from checked-out sources
- prebuilt-image presets: run published container images

## Compose presets

Source-build mode:

- `deploy/compose/compose.source.yaml`

Prebuilt-image mode:

- `deploy/compose/compose.image.yaml`

## Config files

- `deploy/config/config.issuers.example.yml`: local issuer example compatible with current core parser
- `deploy/config/config.yml`: local copy used by `*.image.yaml` files (create from compatible example)

## Quick start

Source-build:

```bash
cd deploy/compose
mkdir -p runtime/core-data

docker compose -f compose.source.yaml up --build
```

Prebuilt-image:

```bash
cd deploy/compose
cp ../config/config.issuers.example.yml ../config/config.yml
mkdir -p runtime/core-data

ACMED_TOKEN_ADMIN='replace-me' \
docker compose -f compose.image.yaml up
```

Health checks:

```bash
curl -s http://127.0.0.1:8443/healthz
curl -s http://127.0.0.1:8443/acme/directory
```
