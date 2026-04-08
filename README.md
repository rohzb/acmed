# acmed

> [!TIP]
> Start with [`docs/overview.md`](docs/overview.md) for the project overview.

## Overview

This directory contains the design and implementation guidance for `acmed`, a small, policy-driven certificate broker with a broker-native API, a SQLite-backed worker loop, and an optional ACME-compatible adapter.

The document set is organized under [`docs/`](docs/) so this directory can serve as a clean future repository root.

## Documents

- Project overview, constraints, and success criteria: [`docs/overview.md`](docs/overview.md)
- System shape, boundaries, and package layout: [`docs/architecture.md`](docs/architecture.md)
- Lifecycle, schema, storage, configuration, and broker API shape: [`docs/data-model.md`](docs/data-model.md)
- Security defaults and runtime expectations: [`docs/security-operations.md`](docs/security-operations.md)
- Delivery order, stop rules, and MVP completion criteria: [`docs/delivery-plan.md`](docs/delivery-plan.md)
- Execution checklist: [`docs/implementation-checklist.md`](docs/implementation-checklist.md)
- Code generation and implementation conventions: [`docs/implementation-guide.md`](docs/implementation-guide.md)
- ACME-visible protocol behavior: [`docs/acme-api-reference.md`](docs/acme-api-reference.md)
- ACME client smoke tests and compatibility notes: [`docs/acme-compatibility.md`](docs/acme-compatibility.md)

If two documents appear to disagree:

1. Prefer the document listed above for that topic.
2. Prefer delivery sequencing from [`docs/delivery-plan.md`](docs/delivery-plan.md) over broader checklists or examples.
3. Prefer explicit protocol rules in [`docs/acme-api-reference.md`](docs/acme-api-reference.md) over implied behavior in other docs.

## Purpose

Use these documents to guide an incremental implementation that stays small, secure, testable, and truthful about what is supported at each stage.
