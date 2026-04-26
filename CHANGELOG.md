# Changelog

All notable changes to this project are documented in this file.

The format is inspired by Keep a Changelog and follows the repository policy in
`docs/reference/versioning.md`.

## [0.2.1] - 2026-04-26

### Added
- Added explicit worker audit event `order.issuance_failed` with artifact path
  metadata when issuer execution fails.

### Changed
- Improved worker failure reporting so runtime errors include concise issuer
  stderr/stdout context and direct artifact log file paths.

## [0.2.0] - 2026-04-25

### Added
- Added dual issuer execution modes (`local` and `remote`) to support plugin
  architecture evolution.
- Added the `remote_http` issuer adapter with startup capability and version
  checks.
- Added remote issuer configuration fields for endpoint, auth, and timeout
  behavior.
- Added unified deployment bundles under `deploy/` with both source-build
  compose presets (`compose.*.source.yaml`) and prebuilt-image presets
  (`compose.*.image.yaml`).
- Added migration guidance in `docs/guides/migration-from-gen2-split.md` for
  the gen2 split-to-single-repo consolidation.

### Changed
- Normalized issuer `reason_code` propagation in issuance results for clearer
  downstream error handling.
- Hardened and clarified GitHub Actions workflows, including Docker smoke-test
  health-probe reliability and explicit probe progress logging.
- Upgraded workflow actions to current major versions and enabled Node 24
  JavaScript action runtime usage.
- Consolidated gen2 layout to a single canonical `acmed` repository and removed
  split wrapper directories.
- Renamed published core runtime image references from
  `ghcr.io/rohzb/acmed-core:*` to `ghcr.io/rohzb/acmed:*`.
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
