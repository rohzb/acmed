# acmed

> [!TIP]
> Start with [`docs/overview.md`](docs/overview.md).

`acmed` is a policy-driven ACME service with a thin certificate-brokering core, durable state, and an async worker loop.

For v1, the ACME API is the primary client-facing contract. The broker-native API is a later extension and must not drive first implementation decisions.

This README is a compact index for the docs set.

## Sources Of Truth

- [`docs/overview.md`](docs/overview.md): purpose, constraints, MVP boundaries, success criteria
- [`docs/acme-api-reference.md`](docs/acme-api-reference.md): normative ACME-visible contract
- [`docs/architecture.md`](docs/architecture.md): runtime shape, boundaries, package layout
- [`docs/policy-config.md`](docs/policy-config.md): config schema, identity, policy matching, defaults
- [`docs/data-model.md`](docs/data-model.md): lifecycle, persistence, worker claims, artifacts
- [`docs/security-operations.md`](docs/security-operations.md): security baseline and runtime posture
- [`docs/implementation-plan.md`](docs/implementation-plan.md): delivery order, iteration scope, done criteria
- [`docs/implementation-guide.md`](docs/implementation-guide.md): code-shape and test expectations
- [`docs/acme-compatibility.md`](docs/acme-compatibility.md): practical client/issuer compatibility notes
- [`docs/broker-api-reference.md`](docs/broker-api-reference.md): future broker-native API (secondary, later)

## Precedence Rules

1. [`docs/acme-api-reference.md`](docs/acme-api-reference.md) for ACME-visible behavior
2. the topic-owning document for that area
3. [`docs/implementation-plan.md`](docs/implementation-plan.md) for delivery order and slice boundaries
4. [`docs/broker-api-reference.md`](docs/broker-api-reference.md) only when broker-native scope is explicitly in play

## Reading Paths

- V1 implementation: [`docs/overview.md`](docs/overview.md) -> [`docs/acme-api-reference.md`](docs/acme-api-reference.md) -> [`docs/architecture.md`](docs/architecture.md) -> [`docs/policy-config.md`](docs/policy-config.md) -> [`docs/data-model.md`](docs/data-model.md) -> [`docs/security-operations.md`](docs/security-operations.md) -> [`docs/implementation-plan.md`](docs/implementation-plan.md) -> [`docs/implementation-guide.md`](docs/implementation-guide.md)
- Compatibility validation: [`docs/acme-api-reference.md`](docs/acme-api-reference.md) -> [`docs/acme-compatibility.md`](docs/acme-compatibility.md)
- Later broker-native expansion only: [`docs/broker-api-reference.md`](docs/broker-api-reference.md) -> [`docs/policy-config.md`](docs/policy-config.md) -> [`docs/data-model.md`](docs/data-model.md) -> [`docs/implementation-plan.md`](docs/implementation-plan.md)

## Ambiguity Rule

If details still conflict or remain unclear:

1. Prefer the smallest fail-closed interpretation that preserves the documented MVP.
2. Add the missing rule to the most specific document before expanding implementation scope.
