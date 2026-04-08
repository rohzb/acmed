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
6. [`docs/implementation-checklist.md`](docs/implementation-checklist.md)
7. [`docs/implementation-guide.md`](docs/implementation-guide.md)
8. [`docs/acme-api-reference.md`](docs/acme-api-reference.md)
9. [`docs/acme-compatibility.md`](docs/acme-compatibility.md)

## Purpose

Use these documents to guide an incremental implementation that stays small, secure, testable, and truthful about what is supported at each stage.
