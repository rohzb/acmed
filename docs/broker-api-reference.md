# acmed Broker API Reference

> [!TIP]
> **TL;DR**
> This document defines the broker-native HTTP contract for order creation, order reads, and minimal admin visibility.

Use this document as the source of truth for the broker-native API contract.

Owns: broker-native request and response behavior, status codes, visibility rules, and admin list posture.

## 1. Scope

For the broker-first milestone, keep the broker API contract small and explicit.

## 2. Create Order

### Request

`POST /api/v1/orders` should accept only client-supplied fields.

Recommended request fields:

- `dns_names`
- `common_name` when needed by policy or issuer behavior
- `issuer_name` when the client may select from allowed policy options; otherwise derive it from policy
- `csr_pem` only when the selected request mode is client-provided CSR
- `idempotency_key` when client-driven request deduplication is supported

Create-order request rules:

- reject empty `dns_names`, duplicate names after normalization, malformed names, or a `common_name` not present in `dns_names`
- if `issuer_name` is supplied, treat it as a constraint on policy resolution rather than as an unrestricted override
- if `csr_pem` is supplied, accept it only when the selected policy path permits client-provided CSR mode
- if `csr_pem` is omitted, accept the request only when the selected policy path permits service-generated CSR mode
- reject request bodies that exceed the documented size or SAN-count limits from [`policy-config.md`](./policy-config.md)

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

Requester-facing artifact retrieval posture for the broker-first MVP:

- do not expose artifact download URLs until a concrete retrieval endpoint is documented and implemented
- if artifacts exist, the requester-facing order view may expose only stable logical artifact names or an `artifacts_available` boolean
- keep real artifact retrieval as an admin or later-slice capability until requester-scoped download authorization is specified explicitly

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

## 6. HTTP Status Matrix

Use these broker HTTP statuses as the implementation baseline:

| Action | Condition | Status |
|--------|-----------|--------|
| `POST /api/v1/orders` | new order created | `201 Created` |
| `POST /api/v1/orders` | duplicate active order reused | `200 OK` |
| `POST /api/v1/orders` | malformed or client-correctable input | `400 Bad Request` |
| `POST /api/v1/orders` | missing or invalid authentication | `401 Unauthorized` |
| `POST /api/v1/orders` | authenticated requester not allowed by policy | `403 Forbidden` |
| `POST /api/v1/orders` | idempotency conflict or incompatible duplicate payload | `409 Conflict` |
| `GET /api/v1/orders/<order_id>` | owned order found | `200 OK` |
| `GET /api/v1/orders/<order_id>` | unknown order or not owned by requester | `404 Not Found` |
| `GET /api/v1/orders` | requester-scoped list returned | `200 OK` |
| `GET /api/v1/admin/orders` | authenticated admin list returned | `200 OK` |
| `GET /api/v1/admin/orders` | caller authenticated but not in admin allow-list | `403 Forbidden` |
| any endpoint | unexpected internal failure | `500 Internal Server Error` |

## 7. Error Posture

For the broker-first MVP, keep requester-facing API errors compact and fail closed.

Recommended rules:

- return authentication failures without exposing whether a requested identifier would otherwise have matched policy
- return authorization failures without revealing internal policy names, rule structure, or unrelated allowed domains
- return validation failures with field-level detail only for client-correctable input errors
- reserve internal execution detail for admin and audit views rather than requester-facing responses

Ownership-disclosure rules:

- requester-facing order reads should return `404 Not Found` for both unknown orders and orders owned by a different requester
- requester-facing create-order failures may return `403 Forbidden` for policy denial because the caller already proved identity for its own request
- admin endpoints may return `403 Forbidden` when the caller is authenticated but not in the admin allow-list

## 8. Related Documents

For lifecycle, persistence, artifact layout, and admin-surface boundaries, use [`data-model.md`](./data-model.md).

For configuration and policy-matching behavior, use [`policy-config.md`](./policy-config.md).
