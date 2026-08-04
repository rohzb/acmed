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

## Server Listener Shape

### `server.extra_listeners[]`

| Field | Required | Notes |
|---|---|---|
| `host` | no | Listener bind host; defaults to `0.0.0.0` |
| `port` | yes | Listener port |
| `tls_enabled` | no | Enables TLS for this listener |
| `tls_cert_file` | when TLS enabled | PEM full-chain path |
| `tls_key_file` | when TLS enabled | PEM private-key path |

### `server.listener_certificate`

| Field | Required | Notes |
|---|---|---|
| `enabled` | no | Enables self-bootstrap for configured TLS listener files |
| `domains` | when enabled | DNS names for the listener certificate |
| `issuer_name` | no | Optional configured issuer override |
| `requester_id` | no | Internal requester identity, default `acmed-listener` |
| `requester_ip` | no | Internal requester IP evidence, default `127.0.0.1` |
| `renew_before_days` | no | Renewal window, default `30` |
| `timeout_seconds` | no | Startup wait for issuance, default `600` |

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
- Allow missing listener TLS files at startup only when
  `server.listener_certificate.enabled` is true.
