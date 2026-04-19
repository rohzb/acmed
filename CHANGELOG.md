# Changelog

All notable changes to this project are documented in this file.

The format is inspired by Keep a Changelog and follows the repository policy in
`docs/reference/versioning.md`.

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
