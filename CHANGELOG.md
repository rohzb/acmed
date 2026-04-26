# Changelog

All notable changes to this project are documented in this file.

The format is inspired by Keep a Changelog and follows the repository policy in
`docs/reference/versioning.md`.

## [0.2.6] - 2026-04-26

### Added
- Added `docker/scripts/install-plugin-addons.sh` to install selected plugin
  Python packages and plugin addon dependencies from `ACMED_PLUGIN_DIRS`.

### Changed
- Refactored `docker/Dockerfile` to a single runtime target that installs core
  `acmed` plus selected plugin addons from a full source workspace copy.
- Updated issuer-focused Docker compose profiles to use plugin addon selection
  (`ACMED_PLUGIN_DIRS`) instead of legacy multi-target image variants.
- Updated Docker docs and hardening notes to document the addon-driven runtime
  model and acme.sh reference defaults (`3.1.2`).
- Updated issuer Docker examples and helper scripts for addon mode, including
  `docker-compose.issuers.yml`, `docker-compose.pebble-test.yml`, and
  `docker/scripts/up-with-issuers.sh`.

## [0.2.2] - 2026-04-26

### Fixed
- Normalized `subprocess.TimeoutExpired` stdout/stderr payloads to UTF-8 text
  in CLI issuer wrappers so timeout handling no longer crashes with
  `TypeError: data must be str, not bytes`.
- Added defensive worker-side issuer exception handling that always writes
  `issuer-output.log` and `challenge-output.log`, records an issuance attempt,
  and emits an explicit `order.issuance_failed` audit event even when the
  backend raises unexpectedly.

## [0.2.5] - 2026-04-26

### Fixed
- Added `force_renew` as an issuer profile option for `acme_sh` backends.
- Default behavior is now reuse-first (`force_renew: false`): if `acme.sh`
  returns the existing-cert hint (`Add '--force' to force to renew.`), the
  backend continues with `--install-cert` instead of failing.
- When `force_renew: true`, backend appends `--force` to `acme.sh --issue`.

## [0.2.4] - 2026-04-26

### Fixed
- Restored non-forced renewal as default for `acme_sh` issuance.
- When `acme.sh --issue` returns exit code `2` with
  `Add '--force' to force to renew.`, the backend now reuses existing
  certificate state by continuing with `--install-cert` instead of failing.

## [0.2.3] - 2026-04-26

### Fixed
- Updated the `acme_sh` issuer backend to invoke `acme.sh --issue --force`
  so repeat requests for the same domain do not fail with exit code `2`
  (`Add '--force' to force to renew.`).

## [0.1.7] - 2026-04-19

### Added
- Added dedicated CI workflows for Python test matrix validation and Docker
  build smoke testing.
- Added Trivy-based repository security scanning to the security checks
  workflow.
- Added release gating that verifies security checks succeeded on the tagged
  commit before publishing release artifacts.

### Changed
- Standardized workflow naming and badge labels for clearer human-readable CI
  status (`Python Tests`, `Docker Build Smoke Test`, `Security Checks`,
  `Release Pipeline`).
- Expanded CI Python compatibility checks to run across versions 3.11 through
  3.14.
- Hardened `docker/tests/client.Dockerfile` and test runtime behavior to run as
  a non-root user.
- Updated chain test trust bootstrap to support non-root execution while
  preserving TLS trust validation.

## [0.1.6] - 2026-04-19

### Added
- Added GitHub Actions secret scanning workflow with TruffleHog and Gitleaks.
- Added release automation workflow triggered by `vX.Y.Z` tag pushes to build
  artifacts and publish a GitHub Release.

### Changed
- Hardened scanner supply-chain pinning by locking TruffleHog action to a
  commit SHA and Gitleaks image to an immutable digest.
- Updated Gitleaks invocation to support repository-scoped false-positive
  suppression via `.gitleaksignore`.
- Documented tag-driven release process in the project README.

## [0.1.5] - 2026-04-19

### Changed
- Enforced TLS runtime semantics by requiring certificate and key settings when
  `server.tls_enabled=true`.
- Enabled actual TLS socket wrapping in runtime server startup with TLS 1.2+
  minimum.
- Updated configuration documentation and examples to clearly separate local
  HTTP development mode from TLS-enabled deployments.
- Normalized public tutorial examples to use generic hostnames for open-source
  publishing.
- Simplified test execution so `pytest` works without manual `PYTHONPATH`
  environment setup.

### Added
- Added `tests/conftest.py` path bootstrap for local test imports.
- Added TLS config validation coverage in config tests.

## [0.1.4] - 2026-04-12

### Changed
- Security hardening and pre-release stabilization updates.
- Pebble chain test and diagnostics improvements.

## [0.1.3] - 2026-04-12

### Changed
- Iterative implementation updates prior to release hardening.

## [0.1.2] - 2026-04-12

### Changed
- Security and pre-release merge updates.

## [0.1.1] - 2026-04-12

### Changed
- Initial implementation release.
