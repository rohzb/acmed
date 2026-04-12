# Configuration Schema (Structured)

## Top-level Keys

| Key | Required | Purpose |
|---|---|---|
| `server` | yes | Host/port/TLS runtime settings |
| `identity` | yes | Token and mTLS identity settings |
| `access` | yes | Admin subject allow-list |
| `limits` | yes | Request and rate limits |
| `orders` | yes | TTL and retry settings |
| `acme` | yes | ACME surface settings |
| `storage` | yes | SQLite and artifact paths |
| `workers` | yes | Worker polling and concurrency |
| `issuers` | yes | Issuer profiles |
| `proof_handlers` | yes | Internal proof handlers |
| `authorizers` | yes | Requester authorizers |
| `policies` | yes | Policy matching and issuer restrictions |

## Policy Matcher Shape

### `allowed_domains[]`

| Field | Required | Notes |
|---|---|---|
| `syntax` | yes | `exact`, `suffix`, or `regex` (only if regex mode enabled) |
| `value` | yes | Pattern value for selected syntax |

### `policies[]`

| Field | Required | Notes |
|---|---|---|
| `name` | yes | Unique policy name |
| `requester_match` | yes | How requester is matched |
| `allowed_domains` | yes | Domain constraints |
| `allowed_issuers` | yes | Allowed issuer names |
| `proof_handler` | yes | Internal proof handler name |
| `challenge_validation_mode` | yes | `strict` default, `trusted_bypass` for dev-only policies |

## Key Validation Constraints

- Reject unknown plugin references.
- Reject duplicate issuer names, token subjects, and admin subjects after normalization.
- Reject policies that reference unknown issuers or proof handlers.
- Reject invalid or missing `allowed_domains.syntax`/`value`.
- Reject regex patterns unless regex mode is explicitly enabled.
- Reject non-positive limits/TTLs/retries.
- Reject inline token secrets when `secret_env` is expected.
- Require `trusted_client_ca_file` when `identity.mtls.enabled` is true.
- Reject insecure production TLS combinations unless explicitly marked development-only.
