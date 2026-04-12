# Implementation Gaps And Minimal Additions

This note tracks the small remaining gaps to bring runtime behavior in line with the ACME and security docs.

## Gap 1: ACME challenge robustness and test coverage

Current state:
- `http-01`, `dns-01`, and `tls-alpn-01` validation paths are implemented.
- Unit coverage exists for `dns-01` validation behavior.
- Deterministic integration coverage for live DNS and TLS challenge environments is not yet included in the automated test suite.

Minimal required addition:
- Add integration tests for `dns-01` and `tls-alpn-01` against deterministic local fixtures/environments.
