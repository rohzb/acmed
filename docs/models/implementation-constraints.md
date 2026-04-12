# Implementation Constraints (Structured)

## Core Rules

1. Keep order lifecycle protocol-neutral.
2. Keep issuer-specific logic out of lifecycle state transitions.
3. Keep policy resolution explicit and fail closed on ambiguity.
4. Keep plugin boundaries explicit: authorizers, proof handlers, issuers.
5. Keep storage access isolated and testable.

## Security Rules

1. Never log or return secrets or private keys.
2. Treat all inbound request and plugin inputs as untrusted until validated.
3. Do not let requesters provide executable paths or raw issuer plugin flags.
4. Keep issuer capability separate from requester permission.
5. Keep admin access bound to explicit configured subjects.

## Runtime Rules

1. Enforce limits at request boundary before expensive work.
2. Use atomic claim updates for worker ownership.
3. Keep retry behavior bounded and policy-driven.
4. Persist enough audit context to debug failures without leaking secrets.
5. Keep per-order artifact paths deterministic and isolated.
