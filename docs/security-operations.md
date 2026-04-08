# acmed Security And Operations

> [!TIP]
> **TL;DR**
> This document defines the security baseline, abuse controls, runtime topology, startup expectations, and major failure modes for `acmed`.

Use this document as the source of truth for security defaults, operational expectations, and failure-handling posture.

## 1. Security Baseline

Design for at least these threats:

- unauthorized requesters attempting certificate issuance
- over-broad policy allowing unintended names
- bearer token leakage
- mTLS credential misuse
- malformed input
- incompatible ACME behavior causing client failure
- issuer subprocess abuse or command injection
- leakage of secrets through logs, audit records, or artifacts
- abusive order creation causing resource exhaustion

## 2. Transport And Identity

- require TLS for deployed broker, admin, and ACME endpoints
- allow plain HTTP only for explicit localhost or isolated development mode
- if mTLS is enabled, bind requester identity to the verified client certificate rather than to untrusted headers
- evaluate authorization with deny-by-default behavior
- require explicit requester-to-domain authorization before issuance

Broker-first authentication posture:

- make API-token authentication the required happy-path identity mechanism for Iteration 1
- treat mTLS support as optional until a later slice requires or tests it
- store token secrets outside YAML and compare them using constant-time checks
- keep one stable authenticated subject for the full request lifecycle, including audit writes and deduplication

Admin endpoint posture:

- require normal requester authentication before any admin privilege check
- grant admin access only to explicitly configured subjects from `access.admin_subjects`
- do not infer admin rights from network location, issuer choice, or requested domains

## 3. Authorization Safety

- fail closed on parse errors, missing references, or ambiguous matches
- prefer exact-name or tightly scoped rules over broad wildcard grants
- validate syntax-tagged policy entries at startup so malformed or over-broad entries never reach runtime matching
- do not enable regex-backed policy matching by default; treat it as a higher-risk extension that needs explicit validation limits
- treat the `no-challenge` path as a high-trust policy path that must be explicit and auditable
- restrict broker order access to the original requester or an administrator

## 4. Secret Handling

Do not log:

- private keys
- bearer tokens
- external account binding secrets
- raw mTLS key material

Additional rules:

- avoid passing secrets in subprocess arguments when a safer input method exists
- redact secrets from exception messages before writing them to logs or audit events
- discard sensitive temporary files as soon as practical
- prefer short-lived credentials when integrations allow it

## 5. Command Execution

Command-based issuers must run through controlled subprocess wrappers with:

- explicit argument lists
- bounded execution time
- captured stdout and stderr
- structured exit handling
- fixed executable paths
- minimal sanitized environments
- isolated working directories and output paths

Do not invoke a shell unless there is no safer alternative.

## 6. Artifact And Audit Protection

- redact secrets and credentials from audit events by default
- keep audit logs append-oriented and resistant to accidental overwrites
- store enough context to explain decisions without copying secret-bearing payloads
- classify artifact files by sensitivity and apply permissions accordingly
- write private key material only when explicitly required
- create artifact directories and files with restrictive permissions

## 7. Abuse Controls

- rate-limit order creation per requester identity
- throttle repeated authentication failures
- cap concurrent work per issuer and optionally per requester
- reject obviously excessive SAN counts or request sizes early
- keep renewal and retry logic bounded

Broker-first default limits:

- use the documented defaults from [`policy-config.md`](./policy-config.md) unless a deployment overrides them explicitly
- enforce the request body and SAN-count limits at the HTTP boundary before policy lookup or deduplication
- enforce the per-requester create-order rate limit on authenticated identity rather than on source IP alone

## 8. Runtime Topology

The minimal deployment can run as:

- one process hosting the HTTP API and a background worker thread or task
- one shared SQLite database
- one shared artifacts directory

Operational notes:

- run the service as a dedicated non-root user where possible
- keep database and artifact paths outside publicly served directories
- if API and worker remain in one process, compensate with strict local filesystem permissions and conservative subprocess handling

## 9. Startup Sequence

1. Load YAML configuration.
2. Validate plugin references, ACME settings, security settings, and storage paths.
3. Open or initialize SQLite schema.
4. Start the worker loop.
5. Start HTTP server.

Startup must also fail closed when:

- configured API-token subjects or admin subjects are duplicated after normalization
- mTLS is enabled without a trust anchor
- configured request or retry limits are zero, negative, or unreasonably malformed
- artifact or database paths cannot be created with the required restrictive permissions

## 10. Background Processing Expectations

- APIs should not block on long-running issuance.
- Workers should claim work atomically.
- In-progress orders should be recoverable after restart.
- Order state transitions must remain valid even if an external tool crashes.
- Security-sensitive failures should fail closed rather than silently downgrading behavior.

Worker-claim expectations:

- each in-progress order should have one active worker claim at a time
- claim state should be persisted on the order record rather than in a separate queue system for the broker-first milestone
- claims should expire after a bounded interval so abandoned work can be recovered
- recovery should reclaim only expired or explicitly released claims
- claim acquisition should be implemented with short, atomic SQLite writes

## 11. Failure Modes

| Area | Risk | Expected handling |
|------|------|-------------------|
| SQLite locking | concurrent writers block each other | keep writes short and worker concurrency modest |
| External issuer command failure | non-zero exit or timeout | capture logs, classify failure, retry only when safe |
| DNS challenge propagation delay | validation races ahead of propagation | support wait or retry policy in challenge logic |
| Policy misconfiguration | over-broad authorization | fail closed and surface config validation errors |
| Artifact write failure | certificate not persisted | keep order failed, preserve issuer result metadata, emit audit event |
| Restart during issuance | orphaned in-progress state | recover from persisted attempts and allow controlled retry |
| Token or credential leakage | unauthorized issuance or inspection | require TLS, redaction, hashed token storage, and secret minimization |
| Command injection | arbitrary command execution | validate inputs, use explicit argv, avoid shell execution, sanitize environment |
| Audit oversharing | secrets appear in logs or API output | redact by default and restrict audit access |

## 12. Related Documents

- [`policy-config.md`](./policy-config.md): authorization rules, policy syntax, and matcher behavior
- [`data-model.md`](./data-model.md): worker-claim persistence, artifact layout, and admin-surface boundaries
- [`broker-api-reference.md`](./broker-api-reference.md): requester-facing and admin-facing broker HTTP behavior
