# acmed Broker API Reference

> [!TIP]
> **TL;DR**
> The broker-native API is a secondary future extension. It is intentionally out of scope for the first ACME-first implementation.

Use this file as a compatibility placeholder for the previous filename.

Owns: future broker-native API notes when that later expansion is explicitly in scope.

## 1. Current Status

For v1:

- ACME is the primary client-facing interface
- broker-native API endpoints are not part of the required first implementation
- detailed broker API request and response contracts should not drive v1 architecture or sequencing

## 2. When To Use This File

Use this file only when:

- a later iteration explicitly adds broker-native endpoints, and
- `implementation-plan.md` is updated to bring that scope in

Until then, treat this file as a stable pointer so existing links do not break.

## 3. Primary Sources For V1

- [`acme-api-reference.md`](./acme-api-reference.md): primary ACME-visible contract
- [`architecture.md`](./architecture.md): system shape and boundaries
- [`policy-config.md`](./policy-config.md): policy and issuer configuration
- [`implementation-plan.md`](./implementation-plan.md): delivery order and v1 scope
- [`implementation-guide.md`](./implementation-guide.md): code-shape guidance
