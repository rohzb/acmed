# acmed Broker API Reference

> [!TIP]
> **TL;DR**
> This document defines the broker-native HTTP contract for order creation, order reads, and minimal admin visibility.

Use this document as the source of truth for the broker-native API contract.

## 1. Scope

For the broker-first milestone, keep the broker API contract small and explicit.

## 2. Create Order

### Request

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

### Response

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

## 3. Read Order

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

## 4. List Orders

`GET /api/v1/orders` should return a requester-scoped list of the caller's own orders.

Recommended response shape:

- `orders`: array of compact broker-native order views

Broker-first list rules:

- default ordering should be newest first by `created_at`
- keep the first milestone simple: omit pagination, filtering, and sorting controls unless a real slice requires them
- do not expose other requesters' orders through this endpoint

## 5. Admin Visibility

`GET /api/v1/admin/orders` should return an administrative list of orders for operational inspection.

Recommended response shape:

- `orders`: array of compact broker-native order views

Admin list rules:

- default ordering should be newest first by `created_at`
- include `requester_id` in the admin list view
- keep the first milestone simple: omit pagination, filtering, and sorting controls unless a real slice requires them

## 6. Error Posture

For the broker-first MVP, keep requester-facing API errors compact and fail closed.

Recommended rules:

- return authentication failures without exposing whether a requested identifier would otherwise have matched policy
- return authorization failures without revealing internal policy names, rule structure, or unrelated allowed domains
- return validation failures with field-level detail only for client-correctable input errors
- reserve internal execution detail for admin and audit views rather than requester-facing responses

## 7. Related Documents

For lifecycle, persistence, artifact layout, and admin-surface boundaries, use [`data-model.md`](./data-model.md).

For configuration and policy-matching behavior, use [`policy-config.md`](./policy-config.md).
