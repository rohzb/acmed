# acmed

> [!TIP]
> Start with [`docs/overview.md`](docs/overview.md) for the project overview.

## Overview

This directory contains the design and implementation guidance for `acmed`, a small, policy-driven certificate broker with a broker-native API, a SQLite-backed worker loop, and a runtime-optional ACME-compatible adapter that remains part of the documented MVP scope.

Use this README as the index for the document set.

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

## Implementation Readiness

The document set is intended to be implementation-ready for the broker-first MVP and the documented ACME MVP slice.

Before writing code, confirm these document-level decisions:

- Build in the delivery order from [`docs/delivery-plan.md`](docs/delivery-plan.md); do not start with ACME-first scaffolding.
- Treat [`docs/data-model.md`](docs/data-model.md) as the source of truth for request normalization, lifecycle, storage, deduplication, and broker API shape.
- Treat [`docs/security-operations.md`](docs/security-operations.md) as the source of truth for authentication posture, secret handling, subprocess safety, and runtime guardrails.
- Treat [`docs/acme-api-reference.md`](docs/acme-api-reference.md) as the source of truth for every ACME-visible endpoint, status, and error contract.

Questions an implementer should be able to answer from the docs:

- Which order states exist, who moves them, and when retries or expiration are allowed.
- How requester identity, policy selection, deduplication, and artifact visibility work for the broker API.
- Which ACME features are truly in scope for the MVP and which ones must be rejected explicitly.
- Which tests are required before claiming broker-native or ACME compatibility.

Suggested use:

1. Start with [`docs/overview.md`](docs/overview.md).
2. Use [`docs/architecture.md`](docs/architecture.md), [`docs/data-model.md`](docs/data-model.md), and [`docs/security-operations.md`](docs/security-operations.md) for the system contract.
3. Use [`docs/delivery-plan.md`](docs/delivery-plan.md) and [`docs/implementation-checklist.md`](docs/implementation-checklist.md) for execution.
4. Use the ACME documents when implementing or validating the ACME adapter.

Suggested implementation start order:

1. Implement Iteration 0 and Iteration 1 from [`docs/delivery-plan.md`](docs/delivery-plan.md) before adding real issuer subprocesses or ACME endpoints.
2. Keep the first running slice limited to broker-native happy-path behavior plus the security and storage rules needed to make that slice honest.
3. Add ACME persistence and endpoint work only when the broker-native flow is already passing its own tests.

If two documents appear to disagree:

1. Prefer the document listed above for that topic.
2. Prefer delivery sequencing from [`docs/delivery-plan.md`](docs/delivery-plan.md) over broader checklists or examples.
3. Prefer explicit protocol rules in [`docs/acme-api-reference.md`](docs/acme-api-reference.md) over implied behavior in other docs.

If a coding task still feels ambiguous after reading the docs:

1. Prefer the smallest fail-closed interpretation that preserves the documented MVP.
2. Add the missing rule to the most specific document before expanding implementation scope.
