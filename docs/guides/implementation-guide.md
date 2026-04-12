# acmed Implementation Guide

For strict tooling-oriented rules, see [`../models/implementation-constraints.md`](../models/implementation-constraints.md).

## 1. Goal

This is the practical coding guide for `acmed`.
Use it together with the linked docs for API, config, data model, and security details.

Related docs:

- [`implementation-roadmap.md`](./implementation-roadmap.md) for delivery order and checklists
- [`acme-api.md`](../reference/acme-api.md) for the primary external protocol contract
- [`configuration.md`](../reference/configuration.md) for issuer profiles, request limits, retry bounds, TTL defaults, and identity configuration

## 2. Current Design Decisions

These decisions keep implementation aligned across modules:

- [`acme-api.md`](../reference/acme-api.md) defines ACME-visible behavior
- [`configuration.md`](../reference/configuration.md) defines issuer, policy, and limit semantics
- [`data-model.md`](../architecture/data-model.md) defines lifecycle states, claims, and artifacts
- [`security-operations.md`](./security-operations.md) defines startup and runtime security posture
- [`broker-api.md`](../reference/broker-api.md) remains secondary and out of current scope

If a rule appears in more than one document, follow the most interface-specific or topic-specific one rather than averaging them together.

When docs overlap:

- prefer [`acme-api.md`](../reference/acme-api.md) for ACME-visible request and response behavior
- prefer [`broker-api.md`](../reference/broker-api.md) only for the later secondary broker API
- prefer [`configuration.md`](../reference/configuration.md), [`data-model.md`](../architecture/data-model.md), and [`security-operations.md`](./security-operations.md) for shared core rules

## 3. Implementation Priorities

Prioritize:

- clear domain boundaries
- small, typed interfaces
- explicit state transitions
- testable components
- safe subprocess execution
- secure defaults from the start of v1
- low file count and low runtime overhead

For the v1, prefer a modular monolith over a highly segmented architecture.

## 4. Recommended Lean Package Responsibilities

| Package | Responsibility |
|--------|-----------------|
| `api.py` | Shared admin, health, and any later broker-native endpoints |
| `acme_api.py` | Primary ACME-facing HTTP behavior and translation into the core order model |
| `models.py` | Domain entities, request models, and state values |
| `policy.py` | Policy resolution plus authorizer, proof, and issuer selection logic |
| `auth.py` | Identity extraction, token checks, and mTLS mapping |
| `config.py` | YAML loading and typed settings |
| `storage.py` | SQLite access, schema bootstrap, and artifact path helpers |
| `worker.py` | Background processing loop and order claiming |
| `audit.py` | Structured audit event creation |
| `authorizers/` | Requester authorization implementations |
| `proofs/` | Internal proof and approval implementations |
| `issuers/` | External issuer adapters and result parsing |

Split these files only after they become materially harder to read or maintain.

Entrypoint responsibility:

- `main.py` should load config, initialize storage, start the worker loop, and serve the ACME-first HTTP application for the v1
- the same application may mount the later broker-native interface without reshaping the broker core

## 5. Design Rules For Implementation

1. Keep the order model protocol-neutral.
2. Do not embed issuer-specific logic inside the state machine.
3. Do not let proof handlers mutate persistent order state directly.
4. Keep plugin inputs normalized before they cross the boundary.
5. Return structured results instead of overloaded tuples or dicts.
6. Prefer explicit repositories and services over hidden global state.
7. Keep SQLite access isolated behind clear persistence modules.
8. Make retries deliberate and policy-driven.
9. Avoid abstractions that exist only for symmetry.
10. Prefer plain functions and small classes over framework-like manager objects.
11. Keep the happy path implementable in a small number of files.
12. Fail closed on ambiguous security decisions.
13. Never log or return secrets, private keys, or raw credentials.
14. Treat issuer, proof, and request input as untrusted until validated.
15. Prefer wrapping existing issuer tooling over reimplementing its challenge plugin ecosystem.
16. Keep the distinction explicit between requester authorization and external CA validation.
17. Make issuer selection, domain authorization, and artifact ownership explicit in code and tests.
18. Make DNS normalization and requester-scoped resource ownership explicit rather than implicit.

## 6. Runtime Contracts

Related contracts:

- [`data-model.md`](../architecture/data-model.md): order lifecycle, schema shape, and storage layout
- [`configuration.md`](../reference/configuration.md): configuration examples, issuer profiles, and policy matching rules
- [`acme-api.md`](../reference/acme-api.md): primary ACME-visible HTTP contract
- [`broker-api.md`](../reference/broker-api.md): later secondary broker-native HTTP contract
- [`security-operations.md`](./security-operations.md): security baseline, runtime topology, startup behavior, and failure handling

### Order creation service

Responsibilities:

- validate incoming request shape
- normalize DNS names
- resolve matching policy
- compute deduplication key
- set initial retry and expiration fields
- persist a `pending` order
- rely on the worker loop to pick up pending work

Security responsibilities:

- authenticate the requester before order creation
- authorize requested names with deny-by-default behavior
- reject oversized or obviously abusive requests early
- avoid exposing issuer internals or policy details in user-facing error responses

Implementation defaults for the v1:

- derive one stable requester identity before any policy lookup, dedupe check, or audit write
- normalize DNS identifiers once near the API boundary and pass the normalized form through the rest of the broker core
- resolve one effective policy or fail closed; do not rely on implicit first-match behavior
- make duplicate-create handling explicit so equivalent requests return one logical active order
- compile policy entries from their declared `syntax` value into a small explicit matcher rather than relying on ad hoc string checks throughout the codebase

### Worker processor

Responsibilities:

- claim eligible orders
- move them through legal states
- execute authorizers, proof handlers, and issuers
- persist audit events
- classify retryable and terminal failures
- enforce retry exhaustion and order expiration rules before issuing work

Claiming responsibilities:

- acquire work through atomic SQLite updates on the order row
- persist `claimed_by`, `claimed_at`, and `claim_expires_at`
- clear or refresh claims as processing progresses
- recover only expired or explicitly cleared claims after restart

Security responsibilities:

- stop processing immediately on missing credentials or unsafe execution preconditions
- redact secrets before persisting failure details
- preserve enough context for audit without persisting raw secret-bearing data

Recommended worker processing order:

1. refuse expired or invalidly claimed orders before invoking plugins
2. evaluate requester authorization and record the decision
3. execute the internal proof path required by the selected policy
4. invoke the issuer only after authorization and proof state are both satisfied
5. write artifacts, audit the outcome, and clear or refresh the claim as part of the same final processing slice

### Issuer adapter contract

Issuer adapters should:

- accept a normalized order plus one selected issuer profile
- prepare deterministic subprocess arguments or direct mock behavior
- supply only the documented environment variables required by the chosen issuer profile
- capture stdout, stderr, exit status, and artifact paths
- return structured result objects rather than raw command output

Adapter design guidance:

- keep `acme.sh` and `certbot` wrappers separate rather than forcing a fake shared CLI model
- centralize common subprocess safety helpers only where they actually reduce duplication
- treat external issuer plugin names and credential variables as configuration, not as requester input
- never expose raw issuer credentials back through requester-facing APIs

### Artifact writer

Responsibilities:

- create per-order directory layout
- write certificate assets atomically where practical
- avoid leaking secret material to logs

Security responsibilities:

- create directories and files with restrictive permissions
- distinguish sensitive files such as `private.key` from public certificate outputs
- support cleanup or retention rules for sensitive artifacts

## 7. Configuration Validation Rules

The canonical configuration example lives in [`configuration.md`](../reference/configuration.md).

When implementing config models and validation logic:

- fail startup on unknown plugin references
- fail startup on invalid path configuration
- fail startup on empty policy names or issuer names
- reject policies that omit both identity and domain constraints
- reject configuration that introduces component references the lean runtime does not implement
- reject insecure combinations unless explicitly marked as development-only
- reject missing TLS configuration for non-local deployments
- reject plaintext secret placeholders in committed-style configuration examples
- reject unsupported `allowed_domains` pattern syntax at startup rather than falling back to permissive matching
- reject `allowed_domains` entries that omit `syntax` or `value`
- reject regex-backed policy patterns unless regex policy mode is explicitly enabled by a later implementation slice
- reject duplicate API-token subjects or duplicate admin subjects after normalization
- reject non-positive request limits, retry limits, or claim/order TTL values
- reject inline token secrets in YAML when `secret_env` is the documented configuration path
- reject issuer profiles that reference unsupported adapter types or duplicate names
- reject policies that reference unknown `allowed_issuers` or unknown `proof_handler` values

## 8. Minimum Test Contract

The first code should make the required tests obvious rather than leaving coverage strategy implicit.

Core tests should cover at least:

- config loading and fail-closed validation
- DNS normalization and deduplication behavior
- order state-machine legality
- policy selection ambiguity and deny-by-default behavior
- policy entry parsing and exact versus suffix matching behavior
- worker claim, recovery, and retry classification behavior
- artifact permission handling for sensitive outputs
- API-token authentication, admin allow-list checks, and secret-env loading behavior
- CSR mode selection and rejection behavior for mismatched `csr_pem` versus policy mode
- issuer-profile selection and policy restriction behavior
- prevention of requester access to unapproved issuer profiles

Issuer integration tests should cover at least:

- mock issuer success and failure paths
- one real `acme.sh` or `certbot` wrapper path against a deterministic test environment
- subprocess timeout, environment sanitization, and output capture behavior

ACME API tests should cover at least:

- only the behavior actually documented for the ACME surface
- requester ownership and normalization rules shared with the broker core

## 9. Things To Avoid

Do not:

- build a complex plugin framework before a simple interface works
- hide state transitions inside side effects
- let command execution happen without structured logging and timeout control
- mix runtime state with configuration files
- assume distributed infrastructure for the v1
- leave key public interfaces undocumented
- add placeholder docstrings that restate the function name without explaining behavior
- introduce registry, plugin-discovery, or queue frameworks without a proven need
- split modules early just to mirror abstract architecture boxes
- reimplement `acme.sh` or `certbot` plugin ecosystems inside `acmed`
