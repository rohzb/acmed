# AGENTS.md

This file defines how AI coding assistants should work in this repository.

## Scope

These rules apply to all documentation and code changes inside this project directory.

## Source Of Truth Priority

When instructions conflict, use this order:

1. [`docs/reference/acme-api.md`](docs/reference/acme-api.md) for ACME-visible behavior
2. Topic-owning docs in `docs/reference/` and `docs/architecture/`
3. [`docs/guides/implementation-roadmap.md`](docs/guides/implementation-roadmap.md) for delivery sequencing
4. Existing code under `src/acmed/` and tests under `tests/` for implemented behavior
5. [`docs/reference/broker-api.md`](docs/reference/broker-api.md) only when broker-native work is explicitly requested

## Documentation Structure Contract

- `README.md` is the project entry point.
- `docs/README.md` is the documentation entry point.
- `docs/guides/` explains workflows and operational guidance.
- `docs/reference/` defines normative interfaces and configuration contracts.
- `docs/tutorials/` contains step-by-step flows.
- `docs/architecture/` defines system shape and persistence/lifecycle model.

Do not add duplicate rules across multiple docs. Add a single owner and cross-reference it.

## Documentation Writing Rules For AI

- Keep docs human-readable first, then model-friendly.
- Prefer short sections, explicit headings, and deterministic wording.
- Avoid speculative behavior and invented features.
- Keep commands copy-pasteable.
- Use relative links that resolve from the current file location.
- Update cross-references whenever files are moved.

## Code And Test Expectations

- Keep ACME-first behavior aligned with `docs/reference/acme-api.md`.
- Preserve fail-closed security defaults.
- Add or update tests when behavior changes.
- Prefer small, explicit interfaces over speculative abstractions.
- Do not widen issuer/requester permissions without explicit policy and doc updates.

## Change Hygiene

For any substantial change:

1. Update the owning doc first.
2. Update links in `README.md` and `docs/README.md` if navigation changes.
3. Keep implementation status and gaps docs truthful:
   - [`docs/guides/implementation-status.md`](docs/guides/implementation-status.md)
   - [`docs/guides/implementation-gaps.md`](docs/guides/implementation-gaps.md)

## Out Of Scope Defaults

Unless explicitly requested, do not:

- redesign the broker-native API scope
- add deployment-specific production runbooks outside existing project boundaries
- change legal/licensing terms beyond this repository's current declared files
