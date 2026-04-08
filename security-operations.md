# acmed Security And Operations

> [!TIP]
> **TL;DR**
> This document defines the security baseline, abuse controls, runtime topology, startup expectations, and major failure modes for `acmed`.

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

## 3. Authorization Safety

- fail closed on parse errors, missing references, or ambiguous matches
- prefer exact-name or tightly scoped rules over broad wildcard grants
- treat `"no challenge"` as a high-trust policy path that must be explicit and auditable
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

## 10. Background Processing Expectations

- APIs should not block on long-running issuance.
- Workers should claim work atomically.
- In-progress orders should be recoverable after restart.
- Order state transitions must remain valid even if an external tool crashes.
- Security-sensitive failures should fail closed rather than silently downgrading behavior.

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
