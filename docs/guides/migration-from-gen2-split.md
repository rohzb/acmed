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

The old split between wrapper directories is now encoded in filenames:

- source-build mode: `compose.*.source.yaml`
- prebuilt-image mode: `compose.*.image.yaml`

## Notes

- ACME HTTP API behavior is unchanged by this migration.
- Plugin repositories (`acmed-issuer-*`, plugin SDK/base image) remain separate.
