# ACME API Contract (Structured)

## Support Matrix

| Feature | Requirement |
|---|---|
| Directory URL | required |
| `newNonce` | required |
| `newAccount` | required |
| Account resource | required |
| Account orders resource | required |
| `newOrder` | required |
| Order resource | required |
| Authorization resource | required |
| Challenge resource | required |
| `finalize` | required |
| Certificate download | required |
| DNS identifiers | required |
| Wildcards | optional; only with full `dns-01` support |
| `http-01` | optional; advertise only if implemented |
| `dns-01` | optional; advertise only if implemented |
| `tls-alpn-01` | optional |
| `revokeCert` | optional |
| `keyChange` | optional |
| External Account Binding | required |

## Endpoint Surface

| Path | Method | Required | Notes |
|---|---|---|---|
| `/acme/directory` | `GET` | yes | Returns directory object |
| `/acme/new-nonce` | `HEAD` | yes | `GET` optional for compatibility |
| `/acme/new-account` | `POST` | yes | EAB required in v1 |
| `/acme/account/<account_id>` | `POST-as-GET`, `POST` | yes | Fetch/update account |
| `/acme/account/<account_id>/orders` | `POST-as-GET` | yes | List account orders |
| `/acme/new-order` | `POST` | yes | Create order |
| `/acme/order/<order_id>` | `POST-as-GET` | yes | Poll order |
| `/acme/authz/<authorization_id>` | `POST-as-GET` | yes | Fetch authorization |
| `/acme/challenge/<challenge_id>` | `POST-as-GET`, `POST` | yes | Fetch or acknowledge |
| `/acme/order/<order_id>/finalize` | `POST` | yes | Submit CSR |
| `/acme/cert/<certificate_id>` | `POST-as-GET` | yes | Download certificate |
| `/acme/revoke-cert` | `POST` | no | Optional |
| `/acme/key-change` | `POST` | no | Optional |

## Required Behavioral Constraints

- Signed requests must validate JWS `url`, nonce, and account binding (`jwk` for new account, `kid` after account creation).
- POST-as-GET uses empty payload.
- Every successful signed ACME response returns a fresh `Replay-Nonce`.
- Directory must not advertise unimplemented endpoints.
- Wildcards are allowed only when end-to-end `dns-01` is implemented.

## Minimum Object Fields

### Account

- `status`
- `contact`
- `orders`

### Account orders

- `orders`

### Order

- `status`
- `identifiers`
- `authorizations`
- `finalize`
- `expires` when relevant
- `certificate` when valid
- `error` when invalid and available

### Authorization

- `identifier`
- `status`
- `expires` when relevant
- `challenges`
- `wildcard` when relevant

### Challenge

- `type`
- `url`
- `status`
- `token`
- `validated` when successful
- `error` when validation fails
