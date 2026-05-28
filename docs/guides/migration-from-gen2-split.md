# Migration: Gen2 Split To Single Repo

This note documents the breaking consolidation where `acmed` + `acmed-deploy` wrappers were folded into the main `acmed` repository.

## Path changes

- old: `upstream/acmed_gen2/acmed/compose/*`
- old: `upstream/acmed_gen2/acmed-deploy/compose/*`
- new: `deploy/compose/*` in the canonical `acmed` repository

## Naming changes

- old image: `ghcr.io/rohzb/acmed-core:<tag>`
- new image: `ghcr.io/rohzb/acmed:<tag>`

## Compose mode changes

The deploy layout now keeps one preset per build mode:

- source-build mode: `deploy/compose/compose.source.yaml`
- prebuilt-image mode: `deploy/compose/compose.image.yaml`

## Notes

- ACME HTTP API behavior is unchanged by this migration.
- Core `acmed` runtime now installs `acme.sh` and `certbot` directly; no
  remote issuer sidecar compose stack is required.
