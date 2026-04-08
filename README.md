# acmed

> [!TIP]
> Start with [`docs/overview.md`](docs/overview.md) for the project overview.

`acmed` is a small, policy-driven certificate broker with a broker-native API, durable runtime state, an asynchronous worker loop, and a runtime-optional ACME-compatible adapter that remains part of the documented MVP scope.

This README is the index for the document set.

## Document Ownership

- [`docs/overview.md`](docs/overview.md): project purpose, MVP boundaries, success criteria
- [`docs/architecture.md`](docs/architecture.md): runtime shape, component boundaries, package layout
- [`docs/policy-config.md`](docs/policy-config.md): configuration schema, identity config, policy matching, operational defaults
- [`docs/data-model.md`](docs/data-model.md): order lifecycle, persistence, worker claims, artifact layout
- [`docs/broker-api-reference.md`](docs/broker-api-reference.md): broker-native HTTP contract
- [`docs/security-operations.md`](docs/security-operations.md): security baseline, startup behavior, abuse controls, runtime posture
- [`docs/implementation-plan.md`](docs/implementation-plan.md): delivery order, iteration checklists, stop rules, MVP done criteria
- [`docs/implementation-guide.md`](docs/implementation-guide.md): code-shape guidance, package responsibilities, testing expectations
- [`docs/acme-api-reference.md`](docs/acme-api-reference.md): normative ACME-visible protocol contract
- [`docs/acme-compatibility.md`](docs/acme-compatibility.md): ACME client smoke tests and interoperability notes

## Reading Paths

Use the shortest path for the task at hand:

- orientation: [`docs/overview.md`](docs/overview.md) -> [`docs/architecture.md`](docs/architecture.md)
- broker implementation: [`docs/policy-config.md`](docs/policy-config.md) -> [`docs/data-model.md`](docs/data-model.md) -> [`docs/broker-api-reference.md`](docs/broker-api-reference.md) -> [`docs/security-operations.md`](docs/security-operations.md) -> [`docs/implementation-plan.md`](docs/implementation-plan.md)
- code generation or initial implementation: [`docs/implementation-guide.md`](docs/implementation-guide.md) plus the broker path above
- ACME implementation: [`docs/acme-api-reference.md`](docs/acme-api-reference.md) first, then [`docs/acme-compatibility.md`](docs/acme-compatibility.md)

## Implementation Notes

Before writing code:

- use the owning file above as the authority for that topic
- follow [`docs/implementation-plan.md`](docs/implementation-plan.md) rather than starting with ACME-first scaffolding
- prefer explicit protocol rules in [`docs/acme-api-reference.md`](docs/acme-api-reference.md) over examples or smoke-test notes

If a detail still feels ambiguous after reading the docs:

1. Prefer the smallest fail-closed interpretation that preserves the documented MVP.
2. Add the missing rule to the most specific document before expanding implementation scope.
