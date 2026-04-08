# acmed Data Model

> [!TIP]
> **TL;DR**
> This document defines the broker order lifecycle, the core runtime records, the storage model, and the configuration shape.

Use this document as the source of truth for broker lifecycle, storage, configuration, and broker-native API shape.

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

Field semantics for the broker-first MVP:

- `request_source`: identifies which interface created the order; use `broker_api` for the initial milestone and add values such as `acme_adapter` only when those entry points exist
- `private_key_policy`: states whether key material is service-generated, supplied by CSR, or not stored; for the broker-first milestone, prefer a small explicit set such as `service_generated` and `csr_only`
- `csr_source`: states whether the request supplied a CSR or expects the service to generate key material and CSR; for the broker-first milestone, prefer a small explicit set such as `client_provided` and `service_generated`
- `dedupe_key`: stable key derived from the normalized requester identity, normalized identifiers, issuer choice, and CSR/key mode so duplicate create requests can be recognized deterministically

Idempotency relationship:

- if the client supplies `idempotency_key`, treat it as an additional request-level idempotency signal for create-order handling
- `dedupe_key` remains the server-side canonical deduplication value used to recognize semantically equivalent orders
- do not expose `dedupe_key` as a client-controlled field
- do not require `idempotency_key` for the broker-first milestone

Normalization and deduplication rules for the broker-first MVP:

- normalize all DNS names before policy matching, deduplication, persistence, and CSR comparison
- store normalized names in lowercase ASCII A-label form as the canonical persisted representation across the codebase
- sort the normalized `dns_names` set before computing `dedupe_key` so request ordering does not change identity
- treat duplicate create requests with the same active `dedupe_key` as the same logical order rather than as a second issuance request
- if `idempotency_key` is present and conflicts with the payload previously seen for that requester, return `409 Conflict` instead of silently reusing an unrelated order

Do not turn these fields into large plugin-style registries or open-ended free-form values in the broker-first milestone unless a later iteration proves the need.

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

Do not require a separate transition-history table in the broker-first milestone unless the implementation has a real query or recovery need that audit events cannot satisfy cleanly.

### Retry and expiration record

For the broker-first MVP, keep retry and expiration tracking on the order row.

Minimum fields:

- `retry_count`
- `max_retries`
- `expires_at`

Broker-first retry rules:

- initialize `retry_count` to `0`
- set `max_retries` from configuration or policy using a small bounded default
- move `failed` back to `pending` only when the failure is explicitly classified as retryable and `retry_count < max_retries`
- increment `retry_count` before re-queueing a retry
- keep terminal failures in `failed` once retries are exhausted or the failure is classified as non-retryable

Broker-first expiration rules:

- set `expires_at` when the order is created
- use one bounded lifetime policy for the broker-first milestone rather than per-plugin expiration logic
- move `pending` or `authorized` orders to `expired` when `expires_at` passes before successful issuance
- do not retry or issue expired orders

Retry classification rules for the broker-first MVP:

- classify policy denial, malformed requests, configuration errors, and CSR mismatch as non-retryable
- classify transient SQLite lock contention, bounded DNS propagation waits, and bounded external issuer timeouts as retryable only when the same attempt may succeed without changing the order payload
- persist retry classification in audit metadata so operators can explain why a failed order was or was not re-queued
- do not retry after any failure that could indicate unsafe or ambiguous authorization state

## 3. Schema Shape

For the MVP, prefer a small schema with a few well-chosen tables:

- `orders`
- `issuance_attempts`
- `audit_events`

For the broker-first MVP:

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

Recommended claim algorithm for the broker-first MVP:

- select candidate orders from eligible non-terminal states with expired-or-empty claim fields
- claim one order with a short SQLite transaction that updates both lifecycle state and claim fields together
- treat `claim_expires_at` as a lease, not as proof that the previous worker stopped cleanly
- refresh or clear the claim only from the worker that currently owns `claimed_by`
- prefer small worker concurrency and frequent polling over long claim durations

Do not introduce a separate queue or lease-management subsystem for the broker-first milestone.

If the ACME adapter is enabled later, add only the persistence needed to support the documented ACME contract:

- `acme_accounts`
- `acme_account_orders`
- `acme_authorizations`
- `acme_challenges`
- nonce storage only if the chosen nonce strategy requires durable state

Do not add ACME-specific persistence in the first broker-native milestone unless the implementation has reached the ACME iteration described in [`delivery-plan.md`](./delivery-plan.md).

### 3.2 Minimal ACME Persistence Model

The ACME adapter should map onto the broker core without reshaping the broker order model.

Minimum ACME-specific records once the adapter exists:

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

## 4. Storage Model

### YAML configuration

Used for:

- server settings
- identity providers
- policy definitions
- issuer definitions
- challenge provider definitions
- ACME adapter settings
- storage paths
- worker settings

### SQLite runtime state

Used for:

- orders
- worker claims and recovery metadata
- state transitions
- issuer attempts
- audit events
- deduplication keys

For the broker-first MVP:

- store authorization outcomes in order metadata and audit events unless a separate table is justified
- store state-transition history in audit events unless a separate table is justified
- treat renewal tracking as a later addition unless an implementation slice truly needs it

SQLite also serves as the worker coordination mechanism.

### Filesystem artifacts

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

### Admin surface

For the MVP, keep the admin API intentionally small.

Recommended admin-only endpoints:

- `GET /api/v1/admin/orders`
- `GET /api/v1/admin/orders/<order_id>`
- `GET /api/v1/admin/audit-events/<order_id>`

Admin endpoints should be limited to:

- cross-requester order inspection
- audit inspection
- operational visibility needed for support and troubleshooting

Do not add write-heavy or lifecycle-mutating admin endpoints in the broker-first milestone unless a later document explicitly requires them.

### Health surface

For the broker-first MVP, keep health endpoints minimal.

Recommended health endpoints:

- `GET /health/live`
- `GET /health/ready`

Health endpoint expectations:

- keep them unauthenticated unless deployment policy requires otherwise
- `GET /health/live` should report only that the process is running
- `GET /health/ready` should verify configuration load, SQLite availability, and access to the artifacts root
- do not add deep integration checks or issuer-specific probes to the broker-first readiness contract

## 5. Configuration Shape

Configuration examples should stay aligned with the documented delivery and test strategy:

- start with the broker-native happy path before enabling ACME compatibility
- use local, deterministic settings for routine automated testing
- prefer Pebble-oriented ACME settings for local integration runs
- treat Let’s Encrypt staging as optional external verification rather than the default test target

```yaml
server:
  host: 0.0.0.0
  port: 8443
  tls_enabled: true

identity:
  api_tokens:
    enabled: true
  mtls:
    enabled: false

acme:
  enabled: false
  directory_path: /acme/directory
  supported_challenges:
    - http-01
  revoke_cert_enabled: false
  key_change_enabled: false
  external_account_binding:
    enabled: false

storage:
  sqlite_path: data/acmed.db
  artifacts_root: data/orders

workers:
  poll_interval_seconds: 2
  max_parallel_orders: 4

issuers:
  - name: mock
    type: mock

challenge_providers:
  - name: no-challenge
    type: noop

authorizers:
  - name: subnet-lab
    type: source_subnet
    source_subnets:
      - 10.20.30.0/24

policies:
  - name: lab-broker-happy-path
    requester_match:
      authorizers:
        - subnet-lab
    allowed_domains:
      - host1.lab.example.org
      - host2.lab.example.org
    issuer: mock
    challenge: no-challenge
```

When the implementation reaches the ACME iteration, add a second example or environment-specific override that enables ACME, Pebble-oriented integration settings, and any supported challenge-provider configuration. Do not let the first example imply that wildcard issuance, external ACME backends, or production Let’s Encrypt integration are part of the initial milestone.

## 6. Broker-Native API Shape

For the broker-first milestone, keep the broker API contract small and explicit.

### Request normalization and policy selection

Before persisting a broker-native order:

- authenticate the requester and derive one stable `requester_id`
- normalize all DNS names before policy evaluation
- reject empty identifier sets, malformed names, duplicate names, or a `common_name` that is not present in `dns_names`
- resolve exactly one effective policy for the request

Requester identity rules for the broker-first MVP:

- derive `requester_id` from the authenticated credential rather than from client-supplied request fields
- when API tokens are used, bind `requester_id` to the token's configured subject or principal name
- when mTLS is used, bind `requester_id` to the verified client certificate identity after any configured mapping step
- never allow the requester to override `requester_id` in the JSON payload

Policy resolution rules for the broker-first MVP:

- if no policy matches the authenticated requester and requested identifiers, reject the request
- if more than one policy matches but all selected runtime choices are identical, choose the most specific policy and record the selected policy name in audit metadata
- if more than one policy matches and they disagree on issuer, challenge type, or key/CSR mode, fail closed and require configuration cleanup instead of guessing
- if the client supplies `issuer_name`, treat it as a constraint that must still be allowed by the selected policy rather than as an unrestricted override

Specificity rules for the broker-first MVP:

- prefer exact identifier matches over broader domain patterns
- prefer policies with narrower requester constraints over broader requester constraints
- prefer policies that enumerate fewer allowed domains when both otherwise match the same request
- if two matching policies remain tied after those checks, fail closed instead of relying on file order

### Create order request

`POST /api/v1/orders` should accept only client-supplied fields.

Recommended request fields:

- `dns_names`
- `common_name` when needed by policy or issuer behavior
- `issuer_name` when the client may select from allowed policy options; otherwise derive it from policy
- `csr_pem` only when `csr_source` is `client_provided`
- `idempotency_key` when client-driven request deduplication is supported

Do not require clients to supply internal or computed fields such as:

- `status`
- `request_source`
- `private_key_policy`
- `csr_source`
- `dedupe_key`
- `claimed_by`
- `claimed_at`
- `claim_expires_at`
- `retry_count`
- `max_retries`
- `created_at`
- `updated_at`
- `expires_at`

### Create order response

`POST /api/v1/orders` should return a compact broker-native order view.

Recommended response fields:

- `order_id`
- `status`
- `dns_names`
- `common_name`
- `issuer_name`
- `created_at`
- `expires_at`

Duplicate-create handling:

- if the request resolves to an existing active order for the same `dedupe_key`, return `200 OK` with the existing order view rather than creating a second active order
- if an exact idempotency replay is detected, return the same logical result as the original create request
- if the dedupe or idempotency check collides with a semantically different request, return `409 Conflict`

### Read order response

`GET /api/v1/orders/<order_id>` should return the broker-native order view plus operational state that is safe for the requester to see.

Recommended response fields:

- `order_id`
- `status`
- `dns_names`
- `common_name`
- `issuer_name`
- `created_at`
- `updated_at`
- `expires_at`
- `error_message` when the order is failed or denied
- artifact references only when the requester is allowed to retrieve them

Artifact reference shape should stay minimal. Prefer:

- logical artifact names such as `certificate`, `chain`, `fullchain`
- stable API-relative download paths or artifact ids
- no raw filesystem paths in requester-facing responses

Do not expose internal worker-claim fields, raw audit metadata, raw filesystem paths, or secret-bearing artifact details through the broker-first requester-facing order API.

### List orders response

`GET /api/v1/orders` should return a requester-scoped list of the caller's own orders.

Recommended response shape:

- `orders`: array of compact broker-native order views

Broker-first list rules:

- default ordering should be newest first by `created_at`
- keep the first milestone simple: omit pagination, filtering, and sorting controls unless a real slice requires them
- do not expose other requesters' orders through this endpoint

### Admin list response

`GET /api/v1/admin/orders` should return an administrative list of orders for operational inspection.

Recommended response shape:

- `orders`: array of compact broker-native order views

Admin list rules:

- default ordering should be newest first by `created_at`
- include `requester_id` in the admin list view
- keep the first milestone simple: omit pagination, filtering, and sorting controls unless a real slice requires them

### Broker-native API error posture

For the broker-first MVP, keep requester-facing API errors compact and fail closed.

Recommended rules:

- return authentication failures without exposing whether a requested identifier would otherwise have matched policy
- return authorization failures without revealing internal policy names, rule structure, or unrelated allowed domains
- return validation failures with field-level detail only for client-correctable input errors
- reserve internal execution detail for admin and audit views rather than requester-facing responses
