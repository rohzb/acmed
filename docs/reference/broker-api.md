# acmed Broker API Reference

## 1. Current Status

For v1:

- ACME is the primary client-facing interface
- broker-native API endpoints are not part of the required v1 implementation
- detailed broker API request and response contracts should not drive v1 architecture or sequencing

## 2. When To Use This File

This file becomes relevant when:

- a later iteration explicitly adds broker-native endpoints, and
- `implementation-roadmap.md` is updated to bring that scope in

Until then, this stays as a stable pointer so existing links do not break.

## 3. Primary Sources For V1

- [`acme-api.md`](./acme-api.md): primary ACME-visible contract
- [`system-architecture.md`](../architecture/system-architecture.md): system shape and boundaries
- [`configuration.md`](./configuration.md): policy and issuer configuration
- [`implementation-roadmap.md`](../guides/implementation-roadmap.md): delivery order and v1 scope
- [`implementation-guide.md`](../guides/implementation-guide.md): code-shape guidance
