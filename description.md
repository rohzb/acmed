# acmed Project Brief

> [!TIP]
> **TL;DR**
> `acmed` is a policy-driven certificate broker with a small broker core, a SQLite-backed worker loop, and an optional ACME-compatible adapter layered on top.

## 1. Purpose

This folder contains the working design set for a new Python project named `acmed`.

The project goal is to build a central certificate brokerage service for internal infrastructure. The service accepts certificate requests, evaluates whether the requester is allowed to obtain the requested names, optionally performs challenge validation, delegates issuance to pluggable backends, and stores the resulting artifacts and audit trail.

`acmed` is intentionally not designed as an ACME-first system. ACME support is an integration surface, not the core model.

The preferred implementation style is deliberately lean:

- one service
- one database
- one worker loop
- small modules
- minimal abstractions

## 2. Reading Order

Use the docs in this order:

1. [`description.md`](/workspaces/cfg-pi-wizzy/local/acmed/description.md): high-level scope and success criteria
2. [`architecture.md`](/workspaces/cfg-pi-wizzy/local/acmed/architecture.md): system design, boundaries, data model, security, and runtime model
3. [`implementation-guide.md`](/workspaces/cfg-pi-wizzy/local/acmed/implementation-guide.md): implementation sequence, package layout, config expectations, tests, and acceptance criteria
4. [`acme-api-reference.md`](/workspaces/cfg-pi-wizzy/local/acmed/acme-api-reference.md): authoritative ACME-facing contract, support matrix, endpoints, and client workflow
5. [`iteration-log.md`](/workspaces/cfg-pi-wizzy/local/acmed/iteration-log.md): running log of review actions, decisions, and improvements applied to the design

## 3. Core Product Definition

`acmed` is a certificate broker service that:

- accepts certificate requests through a broker API and, optionally, an ACME adapter
- evaluates authorization against internal policy
- selects an issuer and challenge strategy
- processes issuance asynchronously
- persists runtime state, audit records, and certificate artifacts

The design must preserve this distinction:

- Internal authorization policy decides whether a requester is allowed to ask for a certificate.
- ACME challenge validation proves control of an identifier when required by the selected issuance flow.

Those are related, but they are not the same thing.

## 4. Non-Negotiable Design Directives

1. Keep the broker core protocol-agnostic.
2. Model certificate requests as explicit orders with a strict state machine.
3. Run authorization, challenge handling, and issuance asynchronously through background workers.
4. Keep issuers, challenge providers, and authorizers as separate plugin-style boundaries.
5. Store configuration in YAML, runtime state in SQLite, and certificate artifacts on the filesystem.
6. Require a real requester identity signal such as API tokens or mTLS; source IP may be a policy signal but not the default identity mechanism.
7. Treat "no challenge" as an explicit policy-backed path, not as an ACME shortcut.
8. Build security into the baseline design: TLS by default, deny-by-default authorization, least-privilege execution, secret minimization, and redacted audit logging.
9. Require a fully documented codebase, including file banners, type hints, and complete docstrings for Python code.
10. Prefer the simplest architecture that can work: one process, SQLite-backed coordination, and direct service calls before introducing extra layers.
11. Keep the initial release focused on an MVP rather than full ACME protocol coverage.

## 5. MVP Outcome

The MVP should deliver:

- a broker REST API
- persistent order lifecycle management
- YAML-backed policy and component configuration
- SQLite-backed runtime state
- filesystem-backed artifact storage
- background workers for asynchronous processing
- authorizers for subnet-based and DNS-based checks
- challenge providers for broker-native workflows
- issuers for `mock` and a command-based production-oriented skeleton
- structured logging and audit events
- an ACME adapter compatible with the documented supported feature set and verified against both `certbot` and `acme.sh`
- repository-wide documentation and code-quality rules that enforce self-documenting, fully documented source files

## 6. Fast Summary

If you are implementing from these docs, the shortest accurate summary is:

- Build the broker core first.
- Keep the runtime as a modular monolith.
- Store work and runtime state in SQLite.
- Use the worker loop to process orders asynchronously.
- Keep ACME as a protocol adapter, not the domain model.
- Follow [`acme-api-reference.md`](/workspaces/cfg-pi-wizzy/local/acmed/acme-api-reference.md) exactly for ACME-visible behavior.
- Treat secure defaults and realistic client compatibility as part of the MVP, not later hardening.

## 7. Success Statement

The project succeeds when the service can safely accept a normalized certificate request, determine whether it is authorized under internal policy, execute or skip challenge validation according to explicit rules, issue through a pluggable backend, and return a durable, auditable result without letting ACME concepts drive the core architecture or letting the implementation grow more complex than the problem requires.
