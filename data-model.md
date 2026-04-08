# acmed Data Model

> [!TIP]
> **TL;DR**
> This document defines the broker order lifecycle, the core runtime records, the storage model, and the configuration shape.

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
- `created_at`
- `updated_at`
- `expires_at`
- `error_message`
- `dedupe_key`

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

## 3. Schema Shape

For the MVP, prefer a small schema with a few well-chosen tables:

- `orders`
- `issuance_attempts`
- `audit_events`

Add dedicated authorization tables only if query requirements justify them.

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
- state transitions
- issuer attempts
- audit events
- deduplication keys
- renewal tracking

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

## 5. Configuration Shape

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
  enabled: true
  directory_path: /acme/directory
  supported_challenges:
    - http-01
    - dns-01
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
  - name: letsencrypt
    type: certbot
    directory_url: https://acme-v02.api.letsencrypt.org/directory

challenge_providers:
  - name: no-challenge
    type: noop
  - name: dns-hook
    type: dns_hook
    command: /usr/local/bin/acmed-dns-hook

authorizers:
  - name: subnet-lab
    type: source_subnet
    source_subnets:
      - 10.20.30.0/24
  - name: dns-match
    type: dns_resolves_to_source

policies:
  - name: lab-network
    requester_match:
      authorizers:
        - subnet-lab
    allowed_domains:
      - "*.lab.example.org"
    issuer: letsencrypt
    challenge: dns-01
```
