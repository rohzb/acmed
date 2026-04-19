# acmed

> ⚠️ **Early-stage project**
> Expect rough edges, changing interfaces, and incomplete pieces.

[![Python Tests](https://github.com/rohzb/acmed/actions/workflows/ci.yml/badge.svg)](https://github.com/rohzb/acmed/actions/workflows/ci.yml)
[![Docker Build Smoke Test](https://github.com/rohzb/acmed/actions/workflows/docker-ci.yml/badge.svg)](https://github.com/rohzb/acmed/actions/workflows/docker-ci.yml)
[![Security Checks](https://github.com/rohzb/acmed/actions/workflows/security-checks.yml/badge.svg)](https://github.com/rohzb/acmed/actions/workflows/security-checks.yml)
[![Release Pipeline](https://github.com/rohzb/acmed/actions/workflows/release.yml/badge.svg)](https://github.com/rohzb/acmed/actions/workflows/release.yml)

`acmed` (ACME Daemon) is a broker that sits between ACME clients and certificate issuance tooling, centralising policy, validation, and orchestration.

It is not a CA and does not replace ACME servers like Let's Encrypt or step-ca.

---

## Why this exists

ACME automation gets awkward fast in segmented or controlled environments.

- HTTP challenges are often not reachable
- DNS challenges require broader permissions than you want to hand out
- many appliances only implement parts of ACME
- the result is usually host-specific scripts and workarounds

`acmed` puts one service in the middle so that:

- policy lives in one place
- validation is consistent
- issuance is delegated in a controlled way

Instead of solving ACME per host, you solve it once.

---

## What it does (and does not do)

`acmed` accepts ACME requests, tracks their state, applies local policy and proof rules, and delegates actual issuance to external tools.

It intentionally does **not** reimplement issuance logic. Tools like `certbot` or `acme.sh` are used as-is via adapters.

Current scope is intentionally narrow:

- ACME request handling
- policy + proof resolution
- backend delegation

The structure allows extending this into a more generic broker later (e.g. multiple backends), but that is secondary to keeping the current flow simple and predictable.

---

## Typical use cases

- Internal services in segmented networks where HTTP challenges are not reachable
- Environments where DNS credentials must not be distributed to many hosts
- Appliances that support ACME but cannot solve challenges themselves
- Centralised control over who can request which certificates

---

## Request flow

In short:

- client sends ACME request
- `acmed` validates it (identity, source IP, domain rules, etc.) and stores state
- worker selects proof method (HTTP, DNS, implicit trust rules, …)
- issuer adapter runs external tooling (`certbot`, `acme.sh`, …)
- result is exposed via standard ACME resources

---

## Trust model (rough sketch)

`acmed` becomes a central decision point.

- authorizers define *who* is allowed to request certificates
- proof handlers define *how* ownership is validated
- issuer adapters perform the actual issuance

This means:

- access to `acmed` must be controlled
- configuration defines your security boundary
- issuer backends should run with minimal required privileges

---

## Installation

Choose one of the following installation paths.

### From source

```bash
git clone https://github.com/rohzb/acmed.git
cd acmed

python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e .
```

### From GitHub release artifacts

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip

# Download wheel/sdist from:
# https://github.com/rohzb/acmed/releases

pip install ./acmed-0.1.7-py3-none-any.whl
```

### From published Docker image

```bash
docker pull ghcr.io/rohzb/acmed:latest
```

Available tags:

* `ghcr.io/rohzb/acmed:latest`
* `ghcr.io/rohzb/acmed:X`
* `ghcr.io/rohzb/acmed:X.Y`
* `ghcr.io/rohzb/acmed:X.Y.Z`

---

## Quick start

If you cloned the repository, the easiest way to try `acmed` is Docker Compose:

```bash
cp docker/.env.example docker/.env
cp docker/config/config.allow-all.yml docker/config/config.yml

docker compose -f docker/docker-compose.yml --env-file docker/.env up --build
```

To run from the published image:

```bash
mkdir -p /opt/acmed/config
cp config.example.yml /opt/acmed/config/config.yml

docker run --rm \
  --name acmed \
  -p 8443:8443 \
  -e ACMED_TOKEN_ADMIN='replace-with-random-token' \
  -v /opt/acmed/config/config.yml:/app/config/config.yml:ro \
  ghcr.io/rohzb/acmed:latest
```

Quick check:

```bash
curl http://127.0.0.1:8443/healthz
curl http://127.0.0.1:8443/acme/directory
```

---

## Configuration

Configuration is YAML-based and split into three main parts:

* **authorizers** — who is allowed
* **proof handlers** — how ownership is validated
* **issuer adapters** — how certificates are issued

Minimal example:

```yaml
authorizers:
  - type: allow_all

proof_handlers:
  - type: none

issuers:
  - name: mock
    type: mock
```

See `config.example.yml` for a more complete setup.

---

## Development

Run tests:

```bash
pytest -v
```

Run locally:

```bash
python -m acmed.main <config.yml>
```

CI workflows:

* `ci`: Python test matrix (`3.11` through `3.14`) + package build validation
* `docker-ci`: Docker build + runtime smoke test (`/healthz`)
* `security-checks`: Trivy + Gitleaks + TruffleHog

---

## Documentation

* Human-facing docs: `docs/`
* Start here: `docs/README.md`
* Versioning: `docs/reference/versioning.md`
* Machine-oriented contracts: `docs/models/`

Project is MIT licensed (`LICENSE`).

---

## Releases

Release automation is triggered by pushing a SemVer tag:

```bash
git tag -a v0.1.7 -m "acmed v0.1.7"
git push origin v0.1.7
```

Make sure:

* `pyproject.toml` version matches the tag
* `CHANGELOG.md` contains the version

On each `vX.Y.Z` tag push, CI will:

* validate version consistency
* run tests
* build Python artifacts (`sdist`, `wheel`)
* build and push Docker images:

  * `X.Y.Z`, `X.Y`, `X`, `latest`
* create a GitHub Release with artifacts

---

Feedback and PRs are welcome.
