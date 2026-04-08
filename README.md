# acmed

> [!TIP]
> Start with [`docs/overview.md`](docs/overview.md) for the project overview.

## Overview

This directory contains the design and implementation guidance for `acmed`, a small, policy-driven certificate broker with a broker-native API, a SQLite-backed worker loop, and a runtime-optional ACME-compatible adapter that remains part of the documented MVP scope.

Use this README as the index for the document set.

## Doc Map

- [`docs/overview.md`](docs/overview.md): project intent, MVP boundaries, success criteria
- [`docs/architecture.md`](docs/architecture.md): runtime shape, boundaries, package layout
- [`docs/data-model.md`](docs/data-model.md): lifecycle, runtime records, persistence, storage model
- [`docs/policy-config.md`](docs/policy-config.md): configuration shape, policy syntax, policy matching
- [`docs/broker-api-reference.md`](docs/broker-api-reference.md): broker-native HTTP contract
- [`docs/security-operations.md`](docs/security-operations.md): security defaults, abuse controls, operational posture
- [`docs/delivery-plan.md`](docs/delivery-plan.md): delivery order, milestone boundaries, stop rules
- [`docs/implementation-checklist.md`](docs/implementation-checklist.md): shortest execution checklist
- [`docs/implementation-guide.md`](docs/implementation-guide.md): code-generation and code-structure guidance
- [`docs/acme-api-reference.md`](docs/acme-api-reference.md): normative ACME-visible protocol contract
- [`docs/acme-compatibility.md`](docs/acme-compatibility.md): client-facing interoperability checks and smoke-test notes

## Reading Paths

Use the shortest path for the task at hand:

- orientation: [`docs/overview.md`](docs/overview.md) -> [`docs/architecture.md`](docs/architecture.md)
- broker implementation: [`docs/data-model.md`](docs/data-model.md) -> [`docs/policy-config.md`](docs/policy-config.md) -> [`docs/broker-api-reference.md`](docs/broker-api-reference.md) -> [`docs/security-operations.md`](docs/security-operations.md) -> [`docs/delivery-plan.md`](docs/delivery-plan.md) -> [`docs/implementation-checklist.md`](docs/implementation-checklist.md)
- code generation or initial implementation: [`docs/implementation-guide.md`](docs/implementation-guide.md) plus the broker path above
- ACME implementation: [`docs/acme-api-reference.md`](docs/acme-api-reference.md) first, then [`docs/acme-compatibility.md`](docs/acme-compatibility.md)

## Implementation Readiness

The document set is stable for implementation of the broker-first MVP and the documented ACME MVP slice.

Before writing code:

- follow the delivery order from [`docs/delivery-plan.md`](docs/delivery-plan.md); do not start with ACME-first scaffolding
- use the file named in the `Doc Map` as the authority for that topic
- prefer explicit protocol rules in [`docs/acme-api-reference.md`](docs/acme-api-reference.md) over examples or smoke-test notes

The docs should answer:

- which order states exist, who moves them, and when retries or expiration are allowed
- how requester identity, policy selection, deduplication, and artifact visibility work for the broker API
- which ACME features are in scope for the MVP, including `http-01`, `dns-01`, and External Account Binding
- which tests are required before claiming broker-native or ACME compatibility

Suggested start order:

1. Implement Iteration 0 and Iteration 1 from [`docs/delivery-plan.md`](docs/delivery-plan.md) before adding real issuer subprocesses or ACME endpoints.
2. Keep the first running slice limited to broker-native happy-path behavior plus the security and storage rules needed to make that slice honest.
3. Add ACME persistence and endpoint work only when the broker-native flow is already passing its own tests.

If a detail still feels ambiguous after reading the docs:

1. Prefer the smallest fail-closed interpretation that preserves the documented MVP.
2. Add the missing rule to the most specific document before expanding implementation scope.
