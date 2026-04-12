# Order Lifecycle (Structured)

## States

- `pending`
- `authorizing`
- `authorized`
- `issuing`
- `issued`
- `failed`
- `denied`
- `expired`

Terminal states:

- `issued`
- `failed`
- `denied`
- `expired`

## Allowed Transitions

| From | To | Meaning |
|---|---|---|
| `pending` | `authorizing` | Worker starts policy evaluation |
| `authorizing` | `authorized` | Authorization passes |
| `authorizing` | `denied` | Authorization fails |
| `authorized` | `issuing` | Proof completed or skipped |
| `issuing` | `issued` | Issuer succeeded |
| `issuing` | `failed` | Issuer failed and no retry remains |
| `pending` | `expired` | Timed out before processing |
| `authorized` | `expired` | Timed out before issuance |
| `failed` | `pending` | Optional retry path |

## Invariants

- Do not issue expired orders.
- Do not retry after terminal authorization failures.
- Claims must be bounded (`claim_expires_at`) to allow worker recovery.
- Deduplication must use normalized identifier representation.
- Artifact and audit writes must not expose secrets.
