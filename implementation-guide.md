# acmed Implementation Guide

> [!TIP]
> **TL;DR**
> Build the broker core first, keep interfaces small, keep the package layout compact, and add the ACME adapter only after the broker flow is solid and the ACME contract can be implemented truthfully.

## 1. Goal

Use this document as the implementation instruction set for generating the initial `acmed` codebase. It turns the project brief and architecture into an implementation order, package plan, configuration contract, testing plan, and acceptance checklist.

For a shorter execution-focused version, use [`implementation-checklist.md`](/workspaces/cfg-pi-wizzy/local/acmed/implementation-checklist.md).

For ACME client smoke-test examples and compatibility notes, use [`acme-compatibility.md`](/workspaces/cfg-pi-wizzy/local/acmed/acme-compatibility.md).

For the intended delivery style and iteration boundaries, use [`incremental-delivery.md`](/workspaces/cfg-pi-wizzy/local/acmed/incremental-delivery.md).

## 2. Implementation Priorities

The code generation effort should optimize for:

- clear domain boundaries
- small, typed interfaces
- explicit state transitions
- testable components
- safe subprocess execution
- secure defaults from the first generated version
- low file count and low runtime overhead

For the MVP, prefer a modular monolith over a highly segmented architecture.

## 3. Build Order

Before Phase 1, make these structural decisions:

- start with a compact package layout
- keep the worker loop SQLite-backed
- do not build a queue abstraction
- do not build registry frameworks
- keep transport, secret handling, and authorization fail-closed by default

### Phase 1: Models and contracts

Implement:

- typed config models
- order domain models
- state machine definitions
- plugin protocols or abstract base classes
- error classes
- security-sensitive value handling rules for identities, secrets, and artifacts

Deliverable:

- the domain layer compiles and tests without any HTTP server

### Phase 2: Persistence and artifacts

Implement:

- SQLite schema and repository layer
- artifact path layout
- audit event persistence
- order deduplication key handling
- secure file and directory permission behavior
- secret-redaction helpers for logs and audit metadata

Deliverable:

- orders can be created, updated, queried, and audited locally

### Phase 3: Broker services

Implement:

- order normalization
- policy resolution
- order creation service
- retry and expiration logic
- worker pickup integration through persisted `pending` orders

Deliverable:

- the broker service can create durable `pending` orders that the worker loop can discover

### Phase 4: API layer

Implement:

- broker API routes
- admin routes
- request and response schemas
- identity extraction from API token or mTLS metadata
- HTTPS or deployment-time TLS expectations
- access control for order reads and admin-only endpoints

Deliverable:

- API tests prove that order creation and order inspection work

### Phase 5: Worker and plugins

Implement:

- worker loop
- authorizer execution
- challenge execution
- issuer execution
- terminal and retry state handling
- fail-closed handling for authorization, secret lookup, and subprocess safety checks

Deliverable:

- a full end-to-end issuance path using a mock issuer

### Phase 6: External issuer skeletons

Implement:

- controlled subprocess execution wrapper
- command-based issuer skeleton
- broker-native challenge-provider skeletons
- sanitized subprocess environment and fixed executable-path handling

Deliverable:

- the external integration surfaces exist without claiming full production readiness

### Phase 7: ACME adapter

Implement:

- the ACME resources defined in [`acme-api-reference.md`](/workspaces/cfg-pi-wizzy/local/acmed/acme-api-reference.md)
- adapter-local models
- RFC 8555-compatible request and response handling for the supported feature set
- explicit identifier support rules, ownership checks, and ACME-compatible error handling
- fixed v1 certificate response format and truthful directory advertisement
- account-orders resource, DNS normalization rules, and explicit EAB posture
- translation tests

Deliverable:

- the adapter interoperates with common clients such as `certbot` and `acme.sh` for the supported feature set without redefining the core broker model

## 3.1 Required Test Stack

Use:

- `pytest` as the required Python test runner
- fast local tests for unit and service behavior
- Pebble as the primary local ACME integration test server
- `certbot` and `acme.sh` for real-client smoke tests
- Let’s Encrypt staging only as optional external verification, not as the default automated dependency

Why:

- `pytest` gives a standard, scriptable Python test entry point
- Pebble is specifically intended for CI and development testing of ACME behavior
- Let’s Encrypt staging is useful, but it is external and less stable for routine automated testing

## 4. Recommended Lean Package Responsibilities

| Package | Responsibility |
|--------|-----------------|
| `api.py` | Broker endpoints, health endpoints, and request validation |
| `acme_api.py` | ACME translation layer and ACME-visible HTTP behavior |
| `models.py` | Domain entities, request models, and state values |
| `policy.py` | Policy resolution plus authorizer and challenge selection logic |
| `auth.py` | Identity extraction, token checks, and mTLS mapping |
| `config.py` | YAML loading and typed settings |
| `storage.py` | SQLite access, schema bootstrap, and artifact path helpers |
| `worker.py` | Background processing loop and order claiming |
| `audit.py` | Structured audit event creation |
| `authorizers/` | Policy evaluation implementations |
| `challenges/` | Broker-native challenge execution implementations |
| `issuers/` | Certificate issuance implementations |

Split these files only after they become materially harder to read or maintain.

## 5. Design Rules for Generated Code

1. Keep the order model protocol-neutral.
2. Do not embed issuer-specific logic inside the state machine.
3. Do not let challenge providers mutate persistent order state directly.
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
14. Treat issuer, challenge, and request input as untrusted until validated.
15. When implementing the ACME adapter, follow client-visible RFC 8555 behavior rather than broker-internal shortcuts.
16. Do not advertise ACME features or challenge types that are not truly implemented end to end.
17. Make ACME identifier support, ownership checks, and error behavior explicit in code and tests.
18. Make DNS normalization and account-scoped resource ownership explicit rather than implicit.

## 6. Runtime Contracts

For order lifecycle, schema shape, storage layout, and configuration examples, see [`data-model.md`](/workspaces/cfg-pi-wizzy/local/acmed/data-model.md).

For security baseline, runtime topology, startup behavior, and failure handling, see [`security-operations.md`](/workspaces/cfg-pi-wizzy/local/acmed/security-operations.md).

### Order creation service

Responsibilities:

- validate incoming request shape
- normalize DNS names
- resolve matching policy
- compute deduplication key
- persist a `pending` order
- rely on the worker loop to pick up pending work

Security responsibilities:

- authenticate the requester before order creation
- authorize requested names with deny-by-default behavior
- reject oversized or obviously abusive requests early
- avoid exposing internal policy details in user-facing error responses

### Worker processor

Responsibilities:

- claim eligible orders
- move them through legal states
- execute authorizers, challenge providers, and issuers
- persist audit events
- classify retryable and terminal failures

Security responsibilities:

- stop processing immediately on missing credentials or unsafe execution preconditions
- redact secrets before persisting failure details
- preserve enough context for audit without persisting raw secret-bearing data

ACME compatibility responsibilities:

- preserve the distinction between broker-native challenge execution and ACME client-driven challenge fulfillment
- expose standard ACME status transitions through the adapter while keeping broker-internal orchestration simple

### Artifact writer

Responsibilities:

- create per-order directory layout
- write certificate assets atomically where practical
- avoid leaking secret material to logs

Security responsibilities:

- create directories and files with restrictive permissions
- distinguish sensitive files such as `private.key` from public certificate outputs
- support cleanup or retention rules for sensitive artifacts

## 7. Configuration Requirements

The canonical configuration example lives in [`data-model.md`](/workspaces/cfg-pi-wizzy/local/acmed/data-model.md).

The initial config model should include:

- server bind settings
- storage paths
- identity provider settings
- worker limits
- issuer definitions
- challenge provider definitions
- authorizer definitions
- policy rules
- logging level or audit options
- transport-security settings
- secret-source settings or secret references
- ACME adapter enablement and directory settings
- ACME supported challenge configuration
- ACME optional endpoint toggles such as revocation and key change
- ACME External Account Binding posture

Validation expectations:

- fail startup on unknown plugin references
- fail startup on invalid path configuration
- fail startup on empty policy names or issuer names
- reject policies that omit both identity and domain constraints
- reject configuration that introduces component references the lean runtime does not implement
- reject insecure combinations unless explicitly marked as development-only
- reject missing TLS configuration for non-local deployments
- reject plaintext secret placeholders in committed-style configuration examples
- reject ACME configuration that advertises unsupported challenge types or required endpoints

## 8. Testing Requirements

At minimum, add tests for:

- valid and invalid state transitions
- order deduplication decisions
- config parsing success and failure
- policy evaluation for subnet and DNS-based authorizers
- mock issuer success and failure
- worker processing from `pending` to `issued`
- denied order handling
- artifact storage writes
- broker API create and read endpoints
- ACME adapter translation boundaries
- ACME account creation and account lookup flow
- ACME `newOrder` to `finalize` to certificate retrieval flow
- POST-as-GET resource fetches
- nonce issuance and bad-nonce retry handling
- ACME challenge acknowledgement and polling behavior
- CSR mismatch and `orderNotReady` style failure cases
- unsupported identifier rejection and wildcard rules
- ACME resource ownership enforcement
- JWS `jwk` versus `kid` handling rules
- DNS identifier normalization behavior
- an end-to-end smoke test with `certbot`
- an end-to-end smoke test with `acme.sh`
- TLS or secure deployment configuration checks
- deny-by-default authorization behavior
- admin endpoint access restrictions
- secret redaction behavior
- safe subprocess invocation behavior
- artifact permission behavior where the platform supports it

Documentation-oriented checks should also verify:

- key modules have top-level docstrings
- public functions and methods are typed
- public classes and methods include docstrings

Testing strategy:

- use `pytest` as the canonical runner for all Python tests
- keep most tests local and deterministic
- prefer realistic service-level tests over excessive mocking
- run ACME integration tests primarily against Pebble
- use real-client smoke tests with `certbot` and `acme.sh` against the local ACME test environment first
- use Let’s Encrypt staging only for optional compatibility verification, pre-release confidence checks, or manual validation

Suggested test layers:

- unit or service tests:
  broker logic, state machine, normalization, validation, policy evaluation
- integration tests:
  SQLite persistence, worker flow, artifact writing, ACME protocol behavior against Pebble
- real-client smoke tests:
  `certbot` and `acme.sh` against the documented supported feature set
- optional external verification:
  Let’s Encrypt staging when appropriate and when the environment supports it

Operational and security-oriented test expectations should stay aligned with [`security-operations.md`](/workspaces/cfg-pi-wizzy/local/acmed/security-operations.md).

## 9. Documentation Requirements

Generate at least:

- package-level `README` or top-level project `README`
- example YAML configuration
- developer testing notes that explain local `pytest`, Pebble integration tests, and optional staging verification
- developer notes describing how to run the API and worker
- limitations and next-step notes for incomplete integrations
- coding standards documentation that states banner, typing, and docstring requirements
- a short architecture note that explains why the MVP intentionally avoids extra moving parts
- a security note that documents default protections, threat assumptions, and operator responsibilities
- an ACME compatibility note that lists supported endpoints, challenge types, and known client-facing limitations
- the authoritative ACME API reference in [`acme-api-reference.md`](/workspaces/cfg-pi-wizzy/local/acmed/acme-api-reference.md)
- explicit notes on ACME identifier support, ownership rules, error behavior, EAB posture, and account-orders behavior

Documentation should emphasize:

- broker-first architecture
- difference between authorization and challenge validation
- current MVP limits
- safe handling of issuer command execution
- the deliberate simplicity of the architecture
- the deliberate use of secure defaults
- the exact ACME feature set offered to common clients
- which optional ACME endpoints are implemented versus intentionally absent

## 10. Acceptance Criteria

The MVP is complete when:

- a client can create a certificate order through the broker API
- the order is persisted and processed asynchronously
- policy evaluation can allow or deny the order
- a mock issuer can produce a successful issued result
- artifacts and audit events are stored durably
- failures transition to a clear terminal or retryable state
- the ACME adapter exists only as a translation layer and does not distort the broker model
- important source files include file banners
- public Python code is type hinted
- important modules, classes, functions, and methods are documented with usable docstrings
- the core runtime remains understandable without reading more than a handful of main files
- non-health endpoints require authentication
- authorization fails closed when policy is missing or ambiguous
- secrets are redacted from logs and audit records
- sensitive artifacts use restrictive permissions
- subprocess-based issuers run through a hardened wrapper rather than raw shell execution
- the ACME adapter can be used by normal clients through a standard directory URL for the documented supported feature set
- the ACME adapter has passed real-client smoke tests with both `certbot` and `acme.sh` for the documented supported feature set

## 11. Avoid During Generation

Do not:

- implement full ACME RFC behavior in the first pass
- build a complex plugin framework before a simple interface works
- hide state transitions inside side effects
- let command execution happen without structured logging and timeout control
- mix runtime state with configuration files
- assume distributed infrastructure for the MVP
- leave key public interfaces undocumented
- add placeholder docstrings that restate the function name without explaining behavior
- introduce registry, plugin-discovery, or queue frameworks without a proven need
- split modules early just to mirror abstract architecture boxes
- default to insecure transport for deployed environments
- store plaintext tokens or private keys in loosely protected locations without an explicit reason
- expose order details to unrelated requesters
- pass unvalidated input into shell commands
- expose broker-native behaviors through the ACME adapter when they conflict with standard ACME client expectations
- call the adapter compatible with common clients without implementing the required ACME resource flow and real-client tests

## 12. Recommended First Milestone

The first milestone should deliver a local development workflow where:

1. YAML config loads successfully.
2. The API accepts a broker order.
3. SQLite stores the order.
4. A worker authorizes it.
5. A mock issuer returns certificate material.
6. The order reaches `issued`.
7. Tests cover the happy path and one denial path.
8. The main order flow remains readable in a compact set of modules.
