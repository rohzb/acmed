# acmed

> [!TIP]
> Start with [`docs/description.md`](docs/description.md) for the project brief and reading order.

## Overview

This directory contains the design and implementation guidance for `acmed`, a small, policy-driven certificate broker with a broker-native API, a SQLite-backed worker loop, and an optional ACME-compatible adapter.

The document set is organized under [`docs/`](docs/) so this directory can serve as a clean future repository root.

## Reading Order

1. [`docs/description.md`](docs/description.md)
2. [`docs/architecture.md`](docs/architecture.md)
3. [`docs/data-model.md`](docs/data-model.md)
4. [`docs/security-operations.md`](docs/security-operations.md)
5. [`docs/incremental-delivery.md`](docs/incremental-delivery.md)
6. [`docs/implementation-guide.md`](docs/implementation-guide.md)
7. [`docs/implementation-checklist.md`](docs/implementation-checklist.md)
8. [`docs/acme-api-reference.md`](docs/acme-api-reference.md)
9. [`docs/acme-compatibility.md`](docs/acme-compatibility.md)

## Document Authority

Use the documents in this folder by topic, not only by reading order.

| Topic | Authoritative document |
|------|-------------------------|
| Project purpose and success criteria | [`docs/description.md`](docs/description.md) |
| System shape and boundaries | [`docs/architecture.md`](docs/architecture.md) |
| Broker lifecycle, schema, storage, and configuration shape | [`docs/data-model.md`](docs/data-model.md) |
| Security defaults and runtime expectations | [`docs/security-operations.md`](docs/security-operations.md) |
| Delivery order, stop rules, and iteration scope | [`docs/incremental-delivery.md`](docs/incremental-delivery.md) |
| Build phases, tests, and acceptance criteria | [`docs/implementation-guide.md`](docs/implementation-guide.md) |
| Day-to-day execution tracking | [`docs/implementation-checklist.md`](docs/implementation-checklist.md) |
| ACME-visible protocol behavior | [`docs/acme-api-reference.md`](docs/acme-api-reference.md) |
| ACME client smoke tests and compatibility notes | [`docs/acme-compatibility.md`](docs/acme-compatibility.md) |

If two documents appear to disagree:

1. Prefer the document listed above for that topic.
2. Prefer delivery sequencing from [`docs/incremental-delivery.md`](docs/incremental-delivery.md) over broader checklists or examples.
3. Prefer explicit protocol rules in [`docs/acme-api-reference.md`](docs/acme-api-reference.md) over implied behavior in other docs.

## Purpose

Use these documents to guide an incremental implementation that stays small, secure, testable, and truthful about what is supported at each stage.
