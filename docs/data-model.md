# acmed Data Model

> [!TIP]
> **TL;DR**
> This document defines the core order lifecycle, runtime records, persistence shape, and storage model.

Use this document as the source of truth for order lifecycle, runtime records, persistence, and storage.

Owns: lifecycle states, persistence shape, worker claims, retry and expiration behavior, and artifact layout.

## 1. Order Lifecycle

Required states:

- `pending`
- `authorizing`
- `authorized`
- `issuing`
- `issued`
- `failed`
- `denied`
- `expired`

Recommended transitions:

| From | To | Meaning |
|------|----|---------|
| `pending` | `authorizing` | Worker begins policy evaluation |
| `authorizing` | `authorized` | Policy evaluation succeeds |
| `authorizing` | `denied` | Policy evaluation rejects the request |
| `authorized` | `issuing` | Challenge handling completed or was explicitly skipped |
| `issuing` | `issued` | Issuer returns a successful result |
| `issuing` | `failed` | Issuance fails and no retry remains |
| `pending` | `expired` | Request timed out before processing |
| `authorized` | `expired` | Authorized order aged out before issuance |
| `failed` | `pending` | Optional retry path if explicitly supported |

Terminal states for v1 should be `issued`, `failed`, `denied`, and `expired`.

## 2. Core Records

The order record is the shared core object for both external interfaces. ACME-specific records should point at that shared order model rather than replace it.

### Order

Minimum fields:

- `id`
- `status`
- `requester_id`
- `request_source`
- `dns_names`
- `common_name`
- `issuer_name`
- `challenge_type`
- `private_key_policy`
- `csr_source`
- `not_before`
- `not_after`
- `claimed_by`
- `claimed_at`
- `claim_expires_at`
- `created_at`
- `updated_at`
- `expires_at`
- `error_message`
- `dedupe_key`

Field semantics for the MVP:

- `request_source`: identifies which interface created the order; use explicit values such as `acme` and `broker_api` so the primary ACME surface and the optional broker API can share one core model
- `private_key_policy`: states whether key material is service-generated, supplied by CSR, or not stored; for the MVP, prefer a small explicit set such as `service_generated` and `csr_only`
- `csr_source`: states whether the request supplied a CSR or expects the service to generate key material and CSR; for the MVP, prefer a small explicit set such as `client_provided` and `service_generated`
- `dedupe_key`: stable key derived from the normalized requester identity, normalized identifiers, issuer choice, and CSR/key mode so duplicate create requests can be recognized deterministically

Idempotency relationship:

- if the client supplies `idempotency_key`, treat it as an additional request-level idempotency signal for create-order handling
- `dedupe_key` remains the server-side canonical deduplication value used to recognize semantically equivalent orders
- do not expose `dedupe_key` as a client-controlled field
- do not require `idempotency_key` for the initial broker API slice

Normalization and deduplication rules for the MVP:

- normalize all DNS names before policy matching, deduplication, persistence, and CSR comparison
- store normalized names in lowercase ASCII A-label form as the canonical persisted representation across the codebase
- sort the normalized `dns_names` set before computing `dedupe_key` so request ordering does not change identity
- treat duplicate create requests with the same active `dedupe_key` as the same logical order rather than as a second issuance request
- if `idempotency_key` is present and conflicts with the payload previously seen for that requester, return `409 Conflict` instead of silently reusing an unrelated order

Do not turn these fields into large plugin-style registries or open-ended free-form values in the MVP unless a later iteration proves the need.

### Authorization decision

Minimum fields:

- `order_id`
- `authorizer_name`
- `decision`
- `reason`
- `evidence`
- `evaluated_at`

### Issuance attempt

Minimum fields:

- `order_id`
- `issuer_name`
- `attempt_number`
- `command`
- `exit_code`
- `stdout_path`
- `stderr_path`
- `started_at`
- `finished_at`
- `result_code`

### Audit event

Minimum fields:

- `id`
- `order_id`
- `event_type`
- `actor_type`
- `actor_id`
- `message`
- `metadata`
- `created_at`

### State transition record

For the MVP, state-transition history may be represented either by:

- append-only audit events with explicit `from_state` and `to_state` metadata, or
- a dedicated transition-history table added only if query needs justify it

Do not require a separate transition-history table in the MVP unless the implementation has a real query or recovery need that audit events cannot satisfy cleanly.

### Retry and expiration record

For the MVP, keep retry and expiration tracking on the order row.

Minimum fields:

- `retry_count`
- `max_retries`
- `expires_at`

Retry rules for the MVP:

- initialize `retry_count` to `0`
- set `max_retries` from configuration or policy using a small bounded default
- move `failed` back to `pending` only when the failure is explicitly classified as retryable and `retry_count < max_retries`
- increment `retry_count` before re-queueing a retry
- keep terminal failures in `failed` once retries are exhausted or the failure is classified as non-retryable

Expiration rules for the MVP:

- set `expires_at` when the order is created
- use one bounded lifetime policy for the MVP rather than per-plugin expiration logic
- move `pending` or `authorized` orders to `expired` when `expires_at` passes before successful issuance
- do not retry or issue expired orders

Retry classification rules for the MVP:

- classify policy denial, malformed requests, configuration errors, and CSR mismatch as non-retryable
- classify transient SQLite lock contention, bounded DNS propagation waits, and bounded external issuer timeouts as retryable only when the same attempt may succeed without changing the order payload
- persist retry classification in audit metadata so operators can explain why a failed order was or was not re-queued
- do not retry after any failure that could indicate unsafe or ambiguous authorization state

## 3. Schema Shape

For the MVP, prefer a small schema with a few well-chosen tables:

- `orders`
- `issuance_attempts`
- `audit_events`

For the MVP:

- keep the latest worker-claim state on the `orders` row
- record state transitions in `audit_events` unless a dedicated transition table becomes clearly necessary
- record authorization decisions in `audit_events` unless a dedicated authorization table becomes clearly necessary

Add dedicated authorization or transition-history tables only if query requirements justify them.

### 3.1 Worker Claim And Recovery Model

To support atomic work claiming and restart recovery, the order row should carry the worker-claim state.

Minimum worker-claim fields:

- `claimed_by`
- `claimed_at`
- `claim_expires_at`

Worker-claim rules:

- a worker claims an order by atomically moving it into an in-progress lifecycle state and setting the claim fields
- only one active claim may exist per order at a time
- a restarted or replacement worker may reclaim an order only after the prior claim has expired or been explicitly cleared
- successful completion or terminal failure should clear the active claim fields
- claim duration should be bounded so stuck workers do not block recovery forever

Recommended claim algorithm for the MVP:

- select candidate orders only from `pending` plus recoverable `authorized` states with expired-or-empty claim fields
- claim one order with a short SQLite transaction that updates both lifecycle state and claim fields together
- treat `claim_expires_at` as a lease, not as proof that the previous worker stopped cleanly
- refresh or clear the claim only from the worker that currently owns `claimed_by`
- prefer small worker concurrency and frequent polling over long claim durations

Recoverable `authorized` state means:

- the order already completed authorization and any required challenge path for that authorization decision
- the order has not reached terminal issuance success or terminal failure
- the worker can resume at the issuance step without re-running authorization side effects that were already recorded as complete

Do not introduce a separate queue or lease-management subsystem for the MVP.

Because ACME is part of the primary MVP surface, add only the persistence needed to support the documented ACME contract:

- `acme_accounts`
- `acme_account_orders`
- `acme_authorizations`
- `acme_challenges`
- nonce storage only if the chosen nonce strategy requires durable state

Do not add ACME-specific persistence beyond the documented contract unless the implementation has reached a later ACME expansion slice described in [`implementation-plan.md`](./implementation-plan.md).

### 3.2 Minimal ACME Persistence Model

The ACME surface should map onto the broker-style core without reshaping the core order model.

Minimum ACME-specific records once the ACME interface exists:

#### ACME account

Minimum fields:

- `id`
- `status`
- `jwk_thumbprint` or equivalent stable account-key identifier
- `contact`
- `created_at`
- `updated_at`

#### ACME account-order link

Minimum fields:

- `account_id`
- `order_id`
- `created_at`

#### ACME authorization

Minimum fields:

- `id`
- `order_id`
- `identifier_type`
- `identifier_value`
- `status`
- `expires_at`
- `wildcard`

#### ACME challenge

Minimum fields:

- `id`
- `authorization_id`
- `type`
- `token`
- `status`
- `validated_at`
- `error_code`
- `error_detail`

#### Nonce handling

The implementation may use either:

- stateless nonces with verifiable server-side encoding, or
- a small nonce store with expiration and one-time-use tracking

Whichever strategy is chosen, it must support the nonce behavior documented in [`acme-api-reference.md`](./acme-api-reference.md).

## 4. Interface Mapping Summary

- `orders` is the shared core table for both ACME and broker API requests
- `request_source` distinguishes which external interface created the order
- ACME account, authorization, and challenge records provide protocol-facing state that references the shared order lifecycle
- requester-facing broker API responses should project from the same shared order and artifact records rather than inventing a parallel data model

## 5. Storage Model

### 5.1 SQLite runtime state

Used for:

- orders
- worker claims and recovery metadata
- state transitions
- issuer attempts
- audit events
- deduplication keys

For the MVP:

- store authorization outcomes in order metadata and audit events unless a separate table is justified
- store state-transition history in audit events unless a separate table is justified
- treat renewal tracking as a later addition unless an implementation slice truly needs it

SQLite also serves as the worker coordination mechanism.

### 5.2 Filesystem artifacts

Used for:

- generated keys
- CSRs
- returned certificates and chains
- per-order command output
- diagnostic logs too large for the database

Recommended per-order files:

- `private.key`
- `request.csr`
- `certificate.pem`
- `chain.pem`
- `fullchain.pem`
- `issuer-output.log`
- `challenge-output.log`

Recommended artifact layout rules:

- store each order under `artifacts_root/<order_id>/`
- create the order directory before invoking any issuer or challenge subprocesses
- write sensitive files such as `private.key` with owner-only permissions
- write issuer and challenge logs into the order directory so audit references can point at stable relative paths
- treat artifact filenames as part of the documented operator interface and avoid renaming them without updating the docs

### 5.3 Admin surface

For the MVP, keep the admin API intentionally small.

Minimum documented admin endpoint:

- `GET /api/v1/admin/orders`

Possible later admin-only inspection endpoints:

- `GET /api/v1/admin/orders/<order_id>`
- `GET /api/v1/admin/audit-events/<order_id>`

Admin endpoints should be limited to:

- cross-requester order inspection
- audit inspection
- operational visibility needed for support and troubleshooting

Do not add write-heavy or lifecycle-mutating admin endpoints in the MVP unless a later document explicitly requires them.

For concrete broker and admin request or response behavior, use [`broker-api-reference.md`](./broker-api-reference.md).

### 5.4 Health surface

For the MVP, keep health endpoints minimal.

Recommended health endpoints:

- `GET /health/live`
- `GET /health/ready`

Health endpoint expectations:

- keep them unauthenticated unless deployment policy requires otherwise
- `GET /health/live` should report only that the process is running
- `GET /health/ready` should verify configuration load, SQLite availability, and access to the artifacts root
- do not add deep integration checks or issuer-specific probes to the readiness contract

## 6. Related Documents

For the broker configuration shape and policy matching rules, use [`policy-config.md`](./policy-config.md).

For ACME-visible object and status behavior, use [`acme-api-reference.md`](./acme-api-reference.md).

For the optional broker-native HTTP contract, use [`broker-api-reference.md`](./broker-api-reference.md).
