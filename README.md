# acmed

> ⚠️ **Early-stage project**
> Expect rough edges, changing interfaces, and incomplete pieces.

[![Python Tests](https://github.com/rohzb/acmed/actions/workflows/ci.yml/badge.svg)](https://github.com/rohzb/acmed/actions/workflows/ci.yml)
[![Docker Build Smoke Test](https://github.com/rohzb/acmed/actions/workflows/docker-ci.yml/badge.svg)](https://github.com/rohzb/acmed/actions/workflows/docker-ci.yml)
[![Secret Leak Scan](https://github.com/rohzb/acmed/actions/workflows/secret-scan.yml/badge.svg)](https://github.com/rohzb/acmed/actions/workflows/secret-scan.yml)
[![Release Pipeline](https://github.com/rohzb/acmed/actions/workflows/release.yml/badge.svg)](https://github.com/rohzb/acmed/actions/workflows/release.yml)

`acmed` (ACME Daemon) is an ACME-first broker service for internal infrastructure.

I built it because ACME automation gets awkward fast in segmented networks. HTTP challenges are often not reachable, DNS challenges can require broader permissions than you want to hand out, and many appliances support only part of the ecosystem. The result is usually a pile of one-off scripts and host-specific workarounds.

`acmed` puts one service in the middle so that policy and request handling live in one place instead of being reinvented per host. It accepts ACME requests, tracks state, applies local authorization/proof rules, and hands issuance work to an adapter.

A key design choice is that `acmed` does not reimplement issuance tooling. It calls existing tools such as `certbot` and `acme.sh`, then focuses on orchestration and policy. Right now the scope is intentionally narrow: ACME-first flow plus controlled backend delegation. The structure leaves room for more broker-like behavior later (for example multiple backends), but that is secondary to keeping the current flow understandable and predictable.

In short, the request path is:

- client sends ACME request
- `acmed` validates and stores it
- worker resolves policy and proof handling
- issuer adapter runs the external issuance/challenge flow
- result is exposed back through normal ACME resources

## Quick start

```bash
git clone https://github.com/rohzb/acmed.git
cd acmed
```

Easiest way to try it:

```bash
cp docker/.env.example docker/.env
cp docker/config/config.allow-all.yml docker/config/config.yml

docker compose -f docker/docker-compose.yml --env-file docker/.env up --build
```

Or run it locally:

```bash
python -m venv .venv
source .venv/bin/activate

pip install -e .

export ACMED_TOKEN_ADMIN='replace-with-random-token'

python -m acmed.main config.example.yml
```

Quick check:

```bash
curl http://127.0.0.1:8443/healthz
curl http://127.0.0.1:8443/acme/directory
```

Configuration is YAML-based around three parts:

- authorizers: who is allowed
- proof handlers: how ownership is checked
- issuer adapters: how certificates are issued

Have a look at `config.example.yml` for a starting point.

## Development

```bash
pytest
```

```bash
python -m acmed.main <config.yml>
```

CI workflows:

- `ci`: Python test matrix (`3.11`, `3.12`) plus package build validation.
- `docker-ci`: Docker image build and runtime smoke test (`/healthz`).
- `secret-scan`: Gitleaks + TruffleHog checks for leaked credentials.

Docs are under `docs/` (start with `docs/README.md`).
Versioning and release policy is defined in `docs/reference/versioning.md`.
Human-facing docs are separate from machine-oriented contracts in `docs/models/`.
Project is MIT licensed (`LICENSE`).

## Releases

Release automation is wired through GitHub Actions on tag push.

Trigger it with an annotated SemVer tag that matches `pyproject.toml`:

```bash
git tag -a v0.1.5 -m "acmed v0.1.5"
git push origin v0.1.5
```

On each `vX.Y.Z` tag push, CI will:

- validate tag format and ensure it matches `project.version`
- verify `CHANGELOG.md` contains that version
- run tests
- build Python artifacts (`sdist` and `wheel`)
- build and push Docker image tags to GHCR:
  - `X.Y.Z`
  - `X.Y`
  - `X`
  - `latest`
- create a GitHub Release with generated notes and attached build artifacts

Feedback and PRs are welcome.
