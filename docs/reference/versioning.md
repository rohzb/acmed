# acmed Versioning And Release Policy

## 1. Scope

This policy defines versioning for:

- the Python project metadata in `pyproject.toml`
- Git release tags
- future Docker image tags
- release notes and changelog entries

## 2. Canonical Version Source

The canonical project version is `project.version` in `pyproject.toml`.

Rules:

- keep exactly one canonical source of truth
- do not duplicate a manually maintained `__version__` constant in code
- build and release tooling must read from `pyproject.toml`

## 3. Version Scheme

`acmed` uses Semantic Versioning (`MAJOR.MINOR.PATCH`) with pre-`1.0.0` rules:

- while `0.y.z`, breaking changes bump `MINOR` (`0.1.0` -> `0.2.0`)
- bug fixes and non-breaking internal/doc/test changes bump `PATCH`
- backward-compatible new capabilities bump `MINOR`
- `1.0.0` is the stability declaration point for public contracts

Contract boundaries are:

- ACME-visible behavior in `docs/reference/acme-api.md`
- configuration contract in `docs/reference/configuration.md`
- public Python entry points in `src/acmed/__init__.py`

## 4. Change Classification

`PATCH`:

- bug fixes without contract changes
- security fixes without interface changes
- refactors, docs, tests, dependency updates without behavioral break

`MINOR`:

- new backward-compatible endpoints or features
- new optional configuration keys
- new issuer/proof/authorizer plugins that do not break existing config

`MAJOR`:

- breaking changes after `1.0.0`
- before `1.0.0`, treat equivalent breaking changes as `MINOR`

## 5. Python Packaging Compatibility (PEP 440)

Released versions:

- `X.Y.Z` only (stable release)

Pre-releases:

- `X.Y.ZrcN` for release candidates
- `X.Y.Z.devN` for development snapshots

Do not publish local version suffixes (`+...`) to public package indexes.

## 6. Git Tag Policy

Use annotated tags for releases:

- format: `vX.Y.Z` (example: `v0.2.3`)
- tag version must match `pyproject.toml` version
- do not move or rewrite published release tags

## 7. Docker Image Tag Policy (Future-Ready)

When publishing images, derive tags from the same project version.

For release `X.Y.Z`, publish:

- `X.Y.Z` (immutable release tag)
- `X.Y` (minor stream)
- `X` (major stream)

Optional moving channel tags:

- `latest` only for the newest stable release
- `edge` or `dev` for non-stable builds

Every image should include OCI labels at minimum:

- `org.opencontainers.image.version`
- `org.opencontainers.image.revision`
- `org.opencontainers.image.source`

## 8. Release Checklist

For each release:

1. classify change level (`PATCH` or `MINOR` while `<1.0.0`)
2. bump `project.version` in `pyproject.toml`
3. update changelog/release notes for that version
4. run tests
5. create annotated tag `vX.Y.Z`
6. build/publish Python artifacts and Docker images from that tag

## 9. CI Validation Recommendations

Automate checks that:

- `pyproject.toml` version is valid PEP 440
- Git tag version equals project version on release jobs
- release tags are annotated and match `vX.Y.Z`
- changelog/release notes include the target version
