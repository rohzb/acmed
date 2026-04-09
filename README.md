# acmed

> [!TIP]
> Start with [`docs/overview.md`](docs/overview.md) for the project overview.

`acmed` is an ACME daemon with a policy-driven certificate-brokering core, durable runtime state, and an asynchronous worker loop. The ACME protocol is the primary product surface. The broker API is a secondary, optional interface for internal integrations and operational control.

This README is the index for the document set.

## Document Ownership

- [`docs/overview.md`](docs/overview.md): project purpose, MVP boundaries, success criteria
- [`docs/acme-api-reference.md`](docs/acme-api-reference.md): normative ACME-visible protocol contract
- [`docs/acme-compatibility.md`](docs/acme-compatibility.md): ACME client smoke tests and interoperability notes
- [`docs/architecture.md`](docs/architecture.md): runtime shape, component boundaries, package layout
- [`docs/policy-config.md`](docs/policy-config.md): configuration schema, identity config, policy matching, operational defaults
- [`docs/data-model.md`](docs/data-model.md): order lifecycle, persistence, worker claims, artifact layout
- [`docs/broker-api-reference.md`](docs/broker-api-reference.md): secondary broker-native HTTP contract
- [`docs/security-operations.md`](docs/security-operations.md): security baseline, startup behavior, abuse controls, runtime posture
- [`docs/implementation-plan.md`](docs/implementation-plan.md): delivery order, iteration checklists, stop rules, MVP done criteria
- [`docs/implementation-guide.md`](docs/implementation-guide.md): code-shape guidance, package responsibilities, testing expectations

## Contract Precedence

When two docs feel close in scope, prefer them in this order:

1. [`docs/acme-api-reference.md`](docs/acme-api-reference.md) for ACME-visible behavior
2. the topic-owning reference document for that area
3. [`docs/implementation-plan.md`](docs/implementation-plan.md) for delivery order and slice boundaries
4. [`docs/acme-compatibility.md`](docs/acme-compatibility.md) for smoke-test expectations and client notes

## How To Use These Docs

Use the smallest document that owns the question:

- project scope and success criteria: [`docs/overview.md`](docs/overview.md)
- ACME-visible protocol behavior: [`docs/acme-api-reference.md`](docs/acme-api-reference.md)
- system shape and boundaries: [`docs/architecture.md`](docs/architecture.md)
- config, identity, and policy rules: [`docs/policy-config.md`](docs/policy-config.md)
- lifecycle, persistence, and artifacts: [`docs/data-model.md`](docs/data-model.md)
- broker-native HTTP behavior: [`docs/broker-api-reference.md`](docs/broker-api-reference.md)
- security and runtime posture: [`docs/security-operations.md`](docs/security-operations.md)
- delivery order: [`docs/implementation-plan.md`](docs/implementation-plan.md)
- code-shape and test expectations: [`docs/implementation-guide.md`](docs/implementation-guide.md)
- client smoke tests and interoperability notes: [`docs/acme-compatibility.md`](docs/acme-compatibility.md)

## Reading Paths

Use the shortest path for the task at hand:

- orientation: [`docs/overview.md`](docs/overview.md) -> [`docs/architecture.md`](docs/architecture.md) -> [`docs/acme-api-reference.md`](docs/acme-api-reference.md)
- ACME implementation: [`docs/acme-api-reference.md`](docs/acme-api-reference.md) -> [`docs/acme-compatibility.md`](docs/acme-compatibility.md) -> [`docs/policy-config.md`](docs/policy-config.md) -> [`docs/security-operations.md`](docs/security-operations.md)
- core implementation: [`docs/architecture.md`](docs/architecture.md) -> [`docs/data-model.md`](docs/data-model.md) -> [`docs/policy-config.md`](docs/policy-config.md) -> [`docs/implementation-guide.md`](docs/implementation-guide.md)
- broker API integration: [`docs/broker-api-reference.md`](docs/broker-api-reference.md) -> [`docs/policy-config.md`](docs/policy-config.md) -> [`docs/data-model.md`](docs/data-model.md)

## Editing Guidance

Before writing code:

- use the owning file above as the authority for that topic
- treat [`docs/acme-api-reference.md`](docs/acme-api-reference.md) as the primary external contract
- keep the broker core independent from ACME protocol mechanics even though ACME is the main product surface
- treat [`docs/broker-api-reference.md`](docs/broker-api-reference.md) as an additive internal interface, not the main identity of the project
- prefer explicit protocol rules in [`docs/acme-api-reference.md`](docs/acme-api-reference.md) over examples or smoke-test notes
- prefer updating the narrowest owning document over scattering the same rule across multiple files

If a detail still feels ambiguous after reading the docs:

1. Prefer the smallest fail-closed interpretation that preserves the documented MVP.
2. Add the missing rule to the most specific document before expanding implementation scope.
