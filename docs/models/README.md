# Model Contracts

This folder contains compact, machine-friendly definitions for tooling, code generation, and automated validation.

Use these files when you need strict structure (schemas, field tables, constraints, transitions).  
For narrative explanations and operator/developer guidance, use the regular docs under `docs/guides/`, `docs/reference/`, and `docs/architecture/`.

## Files

- [`acme-api-contract.md`](acme-api-contract.md): endpoint matrix, required methods, required status behavior, and object minimums
- [`config-schema.md`](config-schema.md): configuration keys, required fields, and validation constraints
- [`order-lifecycle.md`](order-lifecycle.md): lifecycle states, transitions, and invariants
- [`implementation-constraints.md`](implementation-constraints.md): implementation rules and non-negotiable safety constraints
