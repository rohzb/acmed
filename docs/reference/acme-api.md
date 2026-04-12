# acmed ACME API Reference

For automation and machine-checked integrations, see the compact contract in [`../models/acme-api-contract.md`](../models/acme-api-contract.md).

## 1. Purpose

This document is the ACME protocol reference for the `acmed` service surface.

It does not replace RFC 8555, but it gives the project a concrete, implementation-oriented endpoint contract.

Primary reference:

- RFC 8555: https://datatracker.ietf.org/doc/html/rfc8555

## 2. Compatibility Goal

The ACME interface should be usable by typical ACME clients through the directory URL with their normal configuration patterns, including:

- `certbot --server <directory-url>`
- `acme.sh --server <directory-url>`

The interface should behave like a normal ACME server for the documented supported feature set.

## 3. ACME Support Matrix

Use this table to track what the current implementation supports and what it does not.

| Feature | v1 posture |
|---------|------------|
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
| `http-01` | optional; advertise only if truly implemented |
| `dns-01` | optional; advertise only if truly implemented |
| `tls-alpn-01` | optional |
| `revokeCert` | optional |
| `keyChange` | optional |
| External Account Binding | required |

## 4. Base Conventions

### 4.1 Content types

The ACME interface should support:

- `application/jose+json` for signed ACME requests
- `application/problem+json` for ACME-compatible error responses
- `application/pem-certificate-chain` for certificate download in the v1

For the v1, keep the certificate response format fixed rather than negotiable unless real client compatibility requires expansion later.

### 4.2 Authentication model

The ACME interface should follow ACME account-key authentication semantics for ACME operations.

Broker-native authentication such as API tokens or mTLS belongs to the broker API, not to the ACME protocol itself.

### 4.3 Resource fetch model

Except where RFC 8555 says otherwise:

- clients fetch ACME resources using POST-as-GET
- the server must validate the JWS `url` field
- the server must require a valid nonce on signed requests

Request handling rules for the v1:

- every successful signed ACME response should include a fresh `Replay-Nonce`
- POST-as-GET requests should carry an empty payload rather than a semantic request body
- reject unsigned resource fetches even when the resource URL is otherwise guessable
- reject requests addressed to a different account, order, authorization, challenge, or certificate resource than the one identified by the JWS target

### 4.4 Identifier support profile

The v1 ACME interface should explicitly support:

- DNS identifiers

The v1 ACME interface should explicitly reject unless later implemented:

- IP identifiers
- identifier types other than DNS names

Wildcard rules:

- wildcard identifiers should be supported only when `dns-01` validation is available end to end
- wildcard orders must not advertise `http-01`
- if wildcard issuance is not fully implemented, reject wildcard identifiers explicitly rather than silently downgrading behavior

DNS normalization rules:

- normalize DNS identifiers to lowercase before comparison or deduplication
- normalize equivalent representations consistently before policy checks and CSR matching
- handle internationalized names consistently by persisting and comparing identifiers in lowercase ASCII A-label form throughout the implementation
- reject malformed names early rather than letting downstream validation interpret them differently

Canonical identifier rules for the v1:

- compare ACME identifiers, broker policy inputs, and CSR SANs using the same normalized representation
- store the normalized value as the canonical persisted identifier
- preserve wildcard intent explicitly instead of inferring it later from a stripped `*.` prefix

### 4.5 ACME signing rules

The ACME interface should follow the normal ACME signing model:

- `newAccount` requests use a JWS protected header with `jwk`
- requests after account creation use a JWS protected header with `kid`
- all signed requests include a valid nonce and the target `url`
- the server should reject requests that mix `jwk` and `kid` incorrectly

Challenge validation should use normal ACME key-authorization semantics:

- construct key authorization from the challenge token and the account key thumbprint
- validate challenge responses against that key authorization
- keep this ACME key-authorization model separate from broker-native authorization policy

Development-only extension posture:

- a policy-scoped trusted-bypass mode may mark challenge acknowledgements as valid without external probing
- this mode is non-standard and intended only for explicitly trusted development/lab policies
- if enabled, document it clearly and do not claim strict ACME validation equivalence for that policy path

### 4.6 External Account Binding posture

The v1 should require ACME External Account Binding for new account creation.

Required posture:

- advertise `meta.externalAccountRequired: true` in the directory object
- require EAB on `newAccount` for normal account creation
- model the EAB secret as an operator-provisioned enrollment credential such as a key identifier plus shared HMAC secret
- reject account-creation attempts that omit EAB or present an invalid EAB payload

Implementation boundary:

- treat EAB as the standards-aligned answer for ACME-side enrollment gating
- keep EAB limited to account bootstrap; normal ACME resource access should continue to use standard account-key authentication after account creation
- if a future non-standard pre-shared-password enrollment mode is ever added, document it separately and do not blur it into the RFC-aligned ACME contract

## 5. Endpoint Summary

| Endpoint | Method | Purpose |
|---------|--------|---------|
| `/acme/directory` | `GET` | Return ACME directory object |
| `/acme/new-nonce` | `HEAD` | Issue replay nonce |
| `/acme/new-account` | `POST` | Create or look up account |
| `/acme/account/<account_id>` | `POST-as-GET`, `POST` | Fetch or update account |
| `/acme/account/<account_id>/orders` | `POST-as-GET` | List account orders |
| `/acme/key-change` | `POST` | Optional account key rollover endpoint |
| `/acme/new-order` | `POST` | Create order |
| `/acme/order/<order_id>` | `POST-as-GET` | Poll order state |
| `/acme/authz/<authorization_id>` | `POST-as-GET` | Fetch authorization state |
| `/acme/challenge/<challenge_id>` | `POST-as-GET`, `POST` | Fetch challenge or acknowledge readiness |
| `/acme/order/<order_id>/finalize` | `POST` | Submit CSR and finalize |
| `/acme/cert/<certificate_id>` | `POST-as-GET` | Download certificate |
| `/acme/revoke-cert` | `POST` | Optional certificate revocation endpoint |

## 6. Endpoint Details

### 6.1 Directory object

Endpoint:

- `GET /acme/directory`

Purpose:

- client entry point
- location map for ACME resources

The directory object should include URLs for:

- `newNonce`
- `newAccount`
- `newOrder`
- `revokeCert` if implemented
- `keyChange` if supported

It may also include:

- `meta.termsOfService`
- `meta.website`
- `meta.caaIdentities`
- `meta.externalAccountRequired`, which should be `true` for the v1

Rules:

- this URL should be stable and documented
- do not advertise optional directory entries for endpoints that are not actually implemented

### 6.2 Nonce endpoint

Endpoint:

- `HEAD /acme/new-nonce`
- `GET /acme/new-nonce` only if you want broader client tolerance

Purpose:

- issue a fresh `Replay-Nonce`

Response requirements:

- return `Replay-Nonce`
- return an ACME-compatible success status
- allow clients to request another nonce after `badNonce` errors

### 6.3 Account endpoints

#### New account

- `POST /acme/new-account`

Purpose:

- create a new ACME account
- optionally look up an existing account with `onlyReturnExisting`

Expected behavior:

- support contact information when supplied
- support agreement flags as needed by policy
- require valid External Account Binding for new account creation
- return `Location` with the account URL
- return the account object

EAB rules for the v1:

- accept `onlyReturnExisting` without requiring a new EAB verification step when the request is only retrieving an already bound account
- bind the created ACME account to the validated EAB credential at account-creation time
- record enough enrollment metadata for audit without persisting raw shared-secret material

Minimum account object fields:

- `status`
- `contact`
- `orders`

Expected account statuses:

- `valid`
- `deactivated`
- `revoked` if supported

#### Account resource

- `POST-as-GET /acme/account/<account_id>`
- `POST /acme/account/<account_id>`

Purpose:

- fetch account details
- update mutable account fields
- support account deactivation if implemented

Ownership rule:

- an account may access or modify only its own account resource

#### Account orders resource

- `POST-as-GET /acme/account/<account_id>/orders`

Purpose:

- return the list of order URLs associated with the account

Ownership rule:

- an account may access only its own orders list resource

Minimum response shape:

- `orders` containing an array of order URLs

#### Key rollover

- `POST /acme/key-change`

Purpose:

- support account key rollover if implemented

Recommended posture:

- mark as unsupported explicitly if not implemented in the v1

### 6.4 Order endpoints

#### New order

- `POST /acme/new-order`

Purpose:

- create a new ACME order for one or more identifiers

Expected request shape:

- identifiers list
- optional `notBefore`
- optional `notAfter`

Validation rules:

- reject unsupported identifier types explicitly
- reject wildcard identifiers unless the server fully supports wildcard issuance through `dns-01`
- reject malformed, duplicate, or empty identifier sets
- reject orders that request identifiers outside the server's documented policy domain, even if the JWS is otherwise valid

Expected response:

- `201 Created`
- `Location` header with the order URL
- order object containing:
  - `status`
  - `authorizations`
  - `finalize`
  - `expires` when relevant

Minimum order object fields:

- `status`
- `identifiers`
- `authorizations`
- `finalize`
- `expires` when relevant
- `certificate` once the order becomes valid

#### Order resource

- `POST-as-GET /acme/order/<order_id>`

Purpose:

- poll order status
- retrieve updated authorization links
- retrieve the certificate URL once the order is valid

Ownership rule:

- only the account that owns the order may read the order resource

Expected status progression:

- `pending`
- `ready`
- `processing`
- `valid`
- `invalid`

Broker-to-ACME status mapping rules:

- ACME `pending` means at least one authorization or challenge is still incomplete
- ACME `ready` means all required authorizations are valid and the order is waiting for `finalize`
- ACME `processing` means finalize succeeded and issuer work is still underway
- ACME `valid` means certificate retrieval is available
- ACME `invalid` means the order can no longer succeed without creating a new order

### 6.5 Authorization endpoint

- `POST-as-GET /acme/authz/<authorization_id>`

Purpose:

- expose the identifier authorization state for the order

Expected response fields:

- `identifier`
- `status`
- `expires` when relevant
- `challenges`
- `wildcard` when relevant

Ownership rule:

- only the account that owns the order may read the authorization resource

Expected statuses:

- `pending`
- `valid`
- `invalid`
- `deactivated`
- `expired`
- `revoked`

Authorization mapping rules for the v1:

- mark an authorization `valid` only after the corresponding challenge path has completed successfully
- mark an authorization `invalid` when challenge validation fails or the order becomes unrecoverable
- do not expose broker-internal policy-evaluation steps as separate ACME authorization states

### 6.6 Challenge endpoint

- `POST-as-GET /acme/challenge/<challenge_id>`
- `POST /acme/challenge/<challenge_id>`

Purpose:

- expose challenge details
- accept the client's acknowledgement that the challenge is ready for validation

Expected challenge types for the v1:

- `http-01`
- `dns-01`
- optionally `tls-alpn-01` if fully implemented

Expected behavior:

- the client provisions the validation material
- the client POSTs to the challenge URL to trigger validation
- the server validates and updates challenge and authorization status
- when an explicitly configured trusted-bypass policy is selected, acknowledgement may mark the challenge valid without external probing

Expected response fields:

- `type`
- `url`
- `status`
- `validated` when successful
- `error` when validation fails
- `token`

Ownership rule:

- only the account that owns the order may read or acknowledge the challenge resource

Do not advertise challenge types that are not actually implemented end to end.

Challenge acknowledgment rules:

- treat repeated acknowledgement of an already terminal challenge as idempotent when the resource owner is unchanged
- reject acknowledgement of a challenge owned by a different account even if the token matches
- return the updated challenge object after acknowledgement so the client can continue polling deterministically

### 6.7 Finalize endpoint

- `POST /acme/order/<order_id>/finalize`

Purpose:

- accept the CSR for the order and begin certificate issuance

Expected request shape:

- `csr` in base64url-encoded DER form

Expected validation rules:

- CSR identifiers must match the order identifiers
- unsupported CSR extensions should be rejected
- finalize should fail cleanly if the order is not ready

Ownership rule:

- only the account that owns the order may finalize it

Expected response behavior:

- return the updated order object
- use `processing` when issuance is still underway
- allow the client to poll the order resource until it becomes `valid` or `invalid`
- once finalize accepts a CSR, do not allow the order identifiers to change

### 6.8 Certificate endpoint

- `POST-as-GET /acme/cert/<certificate_id>`

Purpose:

- return the issued certificate chain for a valid order

Expected behavior:

- make the certificate URL available from the valid order object
- return the certificate chain in `application/pem-certificate-chain`
- ensure unauthorized clients cannot fetch certificate resources for accounts that do not own the order

### 6.9 Revocation endpoint

- `POST /acme/revoke-cert`

Purpose:

- revoke a previously issued certificate

Recommended posture:

- implement if practical for compatibility
- if not implemented in the v1, document that clearly and avoid overstating compatibility

## 7. HTTP Status Guidance

| Endpoint or action | Typical success status |
|--------------------|------------------------|
| `GET /acme/directory` | `200 OK` |
| `HEAD /acme/new-nonce` | `200 OK` or `204 No Content` with `Replay-Nonce` |
| `POST /acme/new-account` creating an account | `201 Created` |
| `POST /acme/new-account` with `onlyReturnExisting` | `200 OK` |
| `POST /acme/new-order` | `201 Created` |
| `POST /acme/challenge/<challenge_id>` acknowledgement | `200 OK` |
| `POST /acme/order/<order_id>/finalize` | `200 OK` |
| `POST-as-GET /acme/order/<order_id>` | `200 OK` |
| `POST-as-GET /acme/cert/<certificate_id>` | `200 OK` |
| ACME problem response | `4xx` or `5xx` as appropriate with `application/problem+json` |

## 8. Minimum Error Contract

The implementation should return ACME-compatible problem documents for at least these cases:

| Condition | Expected ACME-style handling |
|-----------|------------------------------|
| Missing or stale nonce | `badNonce` style error with a fresh nonce available |
| Malformed JWS or invalid payload | malformed request error |
| Unauthorized account access to another account's resource | unauthorized or access-denied style error |
| Unsupported identifier type | rejected identifier style error |
| Wildcard requested without supported `dns-01` path | rejected identifier or unsupported combination error |
| Finalize called before order is ready | `orderNotReady` style error |
| CSR identifiers do not match order identifiers | bad CSR or rejected identifier style error |
| Challenge validation failure | challenge object marked invalid with error details |
| Unsupported endpoint or feature | explicit ACME-compatible error rather than silent omission |

The exact problem `type` values should follow RFC 8555 where applicable.

## 9. Minimum Object Shapes

### Account object

Minimum fields:

- `status`
- `contact`
- `orders`

### Account orders object

Minimum fields:

- `orders`

### Order object

Minimum fields:

- `status`
- `identifiers`
- `authorizations`
- `finalize`
- `expires` when relevant
- `certificate` when valid
- `error` when invalid and an error object is appropriate

### Authorization object

Minimum fields:

- `identifier`
- `status`
- `expires` when relevant
- `challenges`
- `wildcard` when relevant

### Challenge object

Minimum fields:

- `type`
- `url`
- `status`
- `token`
- `validated` when successful
- `error` when validation fails

## 10. Client Workflow Summary

Typical compatible client flow:

1. `GET /acme/directory`
2. `HEAD /acme/new-nonce`
3. `POST /acme/new-account`
4. `POST /acme/new-order`
5. `POST-as-GET` authorization resources
6. Client fulfills challenge
7. `POST` challenge resource to acknowledge readiness
8. `POST-as-GET` order until it becomes `ready`
9. `POST` finalize with CSR
10. `POST-as-GET` order until it becomes `valid`
11. `POST-as-GET` certificate resource

See [`acme-compatibility.md`](../guides/acme-compatibility.md) for client smoke-test examples and compatibility-oriented validation notes.

## 11. Compatibility Boundaries

The ACME interface should be described as compatible with common clients only for the features it truly supports.

That means:

- do not claim full ACME support if `revokeCert`, `keyChange`, or certain challenge types are absent
- do not advertise unsupported challenges
- do not expose broker-native shortcuts through ACME resources
- do not skip nonce, JWS, or POST-as-GET behavior for convenience
- do not claim compatibility with named clients without testing against those named clients

## 12. References

- RFC 8555: https://datatracker.ietf.org/doc/html/rfc8555
- Certbot usage docs: https://eff-certbot.readthedocs.io/en/latest/using.html
- acme.sh server parameter notes: https://github-wiki-see.page/m/acmesh-official/acme.sh/wiki/Server
