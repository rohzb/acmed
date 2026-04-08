# acmed Implementation Guide

> [!TIP]
> **TL;DR**
> Use this document for code structure and generation conventions. Use [`implementation-plan.md`](./implementation-plan.md) for sequencing and iteration scope.

## 1. Goal

Use this document as the implementation instruction set for generating the initial `acmed` codebase. It turns the project overview and architecture into code-shape guidance, package responsibilities, runtime contracts, and validation rules.

Keep this document focused on how to implement the code. The authoritative lifecycle, storage, configuration, API, security, and delivery contracts live in the companion documents it links to.

Owns: code-shape guidance, package responsibilities, validation emphasis, test expectations, and generation constraints.

Companion documents:

- use [`implementation-plan.md`](./implementation-plan.md) for iteration order, scope boundaries, checklists, and MVP done criteria
- use [`acme-api-reference.md`](./acme-api-reference.md) for the normative ACME-visible contract
- use [`acme-compatibility.md`](./acme-compatibility.md) for client smoke-test examples and compatibility notes

## 2. First-slice Implementation Decisions

Use these as cross-document implementation anchors for the first pass:

- use [`policy-config.md`](./policy-config.md) for request limits, retry bounds, TTL defaults, and identity configuration
- use [`broker-api-reference.md`](./broker-api-reference.md) for create-order status behavior, requester visibility rules, and admin access posture
- use [`data-model.md`](./data-model.md) for lifecycle states, worker reclaim eligibility, and artifact layout
- use [`security-operations.md`](./security-operations.md) for startup fail-closed rules and abuse controls

## 3. Implementation Priorities

The code generation effort should optimize for:

- clear domain boundaries
- small, typed interfaces
- explicit state transitions
- testable components
- safe subprocess execution
- secure defaults from the first generated version
- low file count and low runtime overhead

For the MVP, prefer a modular monolith over a highly segmented architecture.

## 4. Recommended Lean Package Responsibilities

| Package | Responsibility |
|--------|-----------------|
| `api.py` | Broker endpoints, admin and health endpoints, and broker request validation |
| `acme_api.py` | ACME translation layer and ACME-visible HTTP behavior when the adapter is enabled |
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

Entrypoint responsibility:

- `main.py` should load config, initialize storage, start the worker loop, and serve the HTTP application for the broker-first MVP
- when ACME is enabled for the documented ACME slices, the same application should mount the ACME routes without reshaping the broker core

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

Authoritative companion contracts:

- [`data-model.md`](./data-model.md): order lifecycle, schema shape, and storage layout
- [`policy-config.md`](./policy-config.md): configuration examples and policy matching rules
- [`broker-api-reference.md`](./broker-api-reference.md): broker-native HTTP contract
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
- avoid exposing internal policy details in user-facing error responses

Implementation defaults for the broker-first MVP:

- derive one stable requester identity before any policy lookup, dedupe check, or audit write
- normalize DNS identifiers once near the API boundary and pass the normalized form through the rest of the broker core
- resolve one effective policy or fail closed; do not rely on implicit first-match behavior
- make duplicate-create handling explicit so equivalent requests return one logical active order
- compile policy entries from their declared `syntax` value into a small explicit matcher rather than relying on ad hoc string checks throughout the codebase

### Worker processor

Responsibilities:

- claim eligible orders
- move them through legal states
- execute authorizers, challenge providers, and issuers
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

ACME compatibility responsibilities:

- preserve the distinction between broker-native challenge execution and ACME client-driven challenge fulfillment
- expose standard ACME status transitions through the adapter while keeping broker-internal orchestration simple

Recommended worker processing order:

1. refuse expired or invalidly claimed orders before invoking plugins
2. evaluate broker authorization and record the decision
3. execute broker-native challenge handling only when the selected policy requires it
4. invoke the issuer only after authorization and challenge state are both satisfied
5. write artifacts, audit the outcome, and clear or refresh the claim as part of the same final processing slice

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

The canonical configuration example lives in [`policy-config.md`](./policy-config.md).

When generating config models and validation logic:

- fail startup on unknown plugin references
- fail startup on invalid path configuration
- fail startup on empty policy names or issuer names
- reject policies that omit both identity and domain constraints
- reject configuration that introduces component references the lean runtime does not implement
- reject insecure combinations unless explicitly marked as development-only
- reject missing TLS configuration for non-local deployments
- reject plaintext secret placeholders in committed-style configuration examples
- reject ACME configuration that advertises unsupported challenge types or required endpoints
- reject unsupported `allowed_domains` pattern syntax at startup rather than falling back to permissive matching
- reject `allowed_domains` entries that omit `syntax` or `value`
- reject regex-backed policy patterns unless regex policy mode is explicitly enabled by a later implementation slice
- reject duplicate API-token subjects or duplicate admin subjects after normalization
- reject non-positive request limits, retry limits, or claim/order TTL values
- reject inline token secrets in YAML when `secret_env` is the documented configuration path

## 8. Minimum Test Contract

The first generated code should make the required tests obvious rather than leaving coverage strategy implicit.

Broker-first tests should cover at least:

- config loading and fail-closed validation
- DNS normalization and deduplication behavior
- order state-machine legality
- policy selection ambiguity and deny-by-default behavior
- policy entry parsing and exact versus suffix matching behavior
- wildcard-identifier authorization behavior against suffix policies
- syntax-tagged regex policy rejection behavior when regex mode is disabled
- worker claim, recovery, and retry classification behavior
- artifact permission handling for sensitive outputs
- broker HTTP status behavior for create-order reuse, policy denial, and hidden unauthorized reads
- API-token authentication, admin allow-list checks, and secret-env loading behavior
- CSR mode selection and rejection behavior for mismatched `csr_pem` versus policy mode

ACME tests should cover at least:

- nonce issuance and bad-nonce recovery behavior
- External Account Binding enforcement for account creation
- account ownership enforcement for account, account orders, order, authorization, challenge, and certificate resources
- POST-as-GET behavior and JWS `url` validation
- order, authorization, and challenge status progression for both `http-01` and `dns-01`
- finalize CSR matching and certificate retrieval behavior

## 9. Avoid During Generation

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
