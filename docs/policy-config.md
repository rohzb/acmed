# acmed Policy And Configuration

> [!TIP]
> **TL;DR**
> This document defines the runtime configuration shape, policy syntax, matcher semantics, and policy-selection rules.

Use this document as the source of truth for YAML configuration, policy definitions, and policy matching behavior.

Owns: configuration schema, identity and admin config, operational defaults, policy syntax, and policy-selection rules.

## 1. Configuration Shape

Configuration examples should stay aligned with the documented delivery and test strategy:

- treat ACME as the primary external interface for the MVP
- use local, deterministic settings for routine automated testing
- prefer Pebble-oriented ACME settings for local integration runs
- treat Let’s Encrypt staging as optional external verification rather than the default test target

```yaml
server:
  host: 0.0.0.0
  port: 8443
  tls_enabled: true

identity:
  api_tokens:
    enabled: true
    tokens:
      - token_id: lab-client-1
        subject: host1.lab.example.org
        secret_env: ACMED_TOKEN_LAB_CLIENT_1
        roles:
          - requester
  mtls:
    enabled: false
    trusted_client_ca_file: null
    subject_mappings: []

access:
  admin_subjects:
    - acmed-admin

limits:
  max_dns_names_per_order: 25
  max_csr_bytes: 32768
  max_request_body_bytes: 65536
  create_order_rate_limit_per_minute: 30

orders:
  default_ttl_seconds: 3600
  claim_ttl_seconds: 300
  max_retries: 3

acme:
  enabled: true
  directory_path: /acme/directory
  supported_challenges:
    - http-01
    - dns-01
  external_account_binding:
    enabled: true
  revoke_cert_enabled: false
  key_change_enabled: false

storage:
  sqlite_path: data/acmed.db
  artifacts_root: data/orders

workers:
  poll_interval_seconds: 2
  max_parallel_orders: 4

issuers:
  - name: mock
    type: mock

challenge_providers:
  - name: no-challenge
    type: no_challenge

authorizers:
  - name: subnet-lab
    type: source_subnet
    source_subnets:
      - 10.20.30.0/24

policies:
  - name: lab-default-policy
    requester_match:
      authorizers:
        - subnet-lab
    allowed_domains:
      - syntax: exact
        value: host1.lab.example.org
      - syntax: exact
        value: host2.lab.example.org
    issuer: mock
    challenge: no-challenge
```

This example is an ACME-enabled MVP baseline. It keeps the shared runtime small while still reflecting the primary ACME-facing product surface.

The same runtime may still expose the broker API for internal or operational use, but that interface remains secondary to the documented ACME contract.

The `challenge_providers` section in this example represents internal helper paths such as broker-native challenge execution. ACME `http-01` and `dns-01` remain client-visible protocol flows defined by [`acme-api-reference.md`](./acme-api-reference.md) rather than interchangeable broker challenge plugins.

Add environment-specific overrides when needed for Pebble integration, staging verification, or later optional features. Do not let this baseline imply that wildcard issuance, external ACME backends, or production Let’s Encrypt integration are part of the initial milestone.

For the ACME MVP, the enabled ACME configuration should:

- advertise both `http-01` and `dns-01`
- require External Account Binding for account creation
- keep wildcard support disabled unless the full `dns-01` wildcard path is implemented end to end

### 1.1 Interface boundary in configuration

Keep the configuration split conceptually even when one process hosts both surfaces:

- `acme.*` config controls the primary ACME-facing behavior
- `identity.*` and `access.*` primarily control the optional broker API and admin surface
- `authorizers`, `challenge_providers`, `issuers`, `policies`, `storage`, and `workers` belong to the shared broker-style core
- do not model ACME challenge types as interchangeable broker `challenge_providers`

### 1.2 Initial operational defaults

Unless a later slice has a documented reason to override them, use these defaults:

- `limits.max_dns_names_per_order`: `25`
- `limits.max_csr_bytes`: `32768`
- `limits.max_request_body_bytes`: `65536`
- `limits.create_order_rate_limit_per_minute`: `30`
- `orders.default_ttl_seconds`: `3600`
- `orders.claim_ttl_seconds`: `300`
- `orders.max_retries`: `3`

Treat these as explicit documented defaults rather than as placeholders.

### 1.3 Identity and admin configuration

Broker API and admin identity rules:

- support API-token authentication for the broker API and admin surface
- treat each configured API token as one stable requester subject
- resolve `requester_id` from the token's configured `subject`
- read token secret material from an environment variable named by `secret_env` rather than from inline YAML secret text
- reject startup if two enabled tokens resolve to the same `token_id` or same `subject`

mTLS configuration rules:

- allow `mtls.enabled: false` for the default local path
- require `trusted_client_ca_file` when `mtls.enabled: true`
- if mTLS subject mappings are configured, apply them after certificate verification and before policy lookup
- reject startup if a mapping would resolve to an empty or duplicate requester subject

Admin configuration rules:

- treat `access.admin_subjects` as the small explicit allow-list for admin endpoints
- require the authenticated subject to appear in `access.admin_subjects` before serving `/api/v1/admin/*`
- do not derive admin privilege from policy matches or requested identifiers

## 2. Policy Matcher Syntax

For the MVP and later extensions, `allowed_domains` entries should declare their matching syntax explicitly.

Recommended policy entry shape:

```yaml
allowed_domains:
  - syntax: exact
    value: host1.lab.example.org
  - syntax: suffix
    value: .lab.example.org
  - syntax: regex
    value: '^([a-z0-9-]+)\\.lab\\.example\\.org$'
```

Required fields:

- `syntax`: declares how `value` must be interpreted
- `value`: the pattern or identifier in the syntax-specific format

Recognized `syntax` values:

- `exact`
- `suffix`
- `regex`

Initial runtime support:

- `exact` and `suffix` are supported
- `regex` must be rejected unless regex policy mode is explicitly enabled

`exact` syntax rules:

- `value` must be one fully normalized DNS identifier such as `host1.lab.example.org`
- an `exact` entry matches only that identifier

`suffix` syntax rules:

- `value` must begin with `.` such as `.lab.example.org`
- a `suffix` entry matches the apex `lab.example.org` and any deeper subdomain under that suffix
- a `suffix` entry is also the explicit policy form that authorizes wildcard request identifiers under that zone when wildcard issuance is otherwise allowed

`regex` syntax rules:

- `value` must be an anchored full-match regular expression over normalized identifiers
- use the regex text directly in `value`; do not prefix it with `regex:` when the surrounding `syntax` field already declares the type
- regex matching must operate on normalized lowercase ASCII A-label identifiers

Disallowed shorthand for all modes:

- bare string entries whose syntax must be inferred from punctuation
- shell-style wildcard syntax such as `*.example.org`
- partial-label wildcards such as `foo*.example.org`
- multiple wildcard labels such as `*.*.example.org`
- wildcard patterns outside the left-most label
- mixed glob-and-regex syntax

Normalization and validation rules for policy matchers:

- normalize `value` according to the declared `syntax` before storing the validated configuration
- reject entries whose `syntax` is unknown
- reject entries whose `value` is malformed for the selected `syntax`
- reject duplicate entries after syntax-aware normalization
- reject regex-backed entries unless regex policy mode is enabled
- reject patterns that are broader than the implementation intends to support

Recommended use:

- prefer `exact` for high-trust issuance paths
- use `suffix` when the policy intentionally covers both a zone apex and its descendants
- treat `regex` as an opt-in expert feature for later slices rather than a default policy-authoring tool
- keep mixed-syntax policies rare unless they are materially simpler than multiple explicit policies

Example mixed-syntax policy:

```yaml
policies:
  - name: lab-general
    requester_match:
      authorizers:
        - subnet-lab
    allowed_domains:
      - syntax: exact
        value: gateway.lab.example.org
      - syntax: suffix
        value: .apps.lab.example.org
    issuer: mock
    challenge: no-challenge
```

## 3. Policy Selection

### 3.1 Request Normalization And Identity

Before persisting an order from any external interface:

- authenticate the requester and derive one stable `requester_id`
- normalize all DNS names before policy evaluation
- reject empty identifier sets, malformed names, duplicate names, or a `common_name` that is not present in `dns_names`
- resolve exactly one effective policy for the request

Requester identity rules for the MVP:

- derive `requester_id` from the authenticated credential rather than from client-supplied request fields
- for ACME requests, bind `requester_id` to the ACME account identity or equivalent stable account-key identifier
- for broker API requests, bind `requester_id` to the token's configured subject or verified mTLS identity after any configured mapping step
- never allow the requester to override `requester_id` in the request payload

Identifier normalization rules apply the same way across both interfaces even when the authentication model differs.

Client input mode rules:

- if the request includes `csr_pem`, treat it as a request for `client_provided` CSR mode
- if the request omits `csr_pem`, treat it as a request for `service_generated` CSR mode
- accept the request only if the selected policy and issuer path support that mode
- reject requests that include `csr_pem` but select a policy path that requires service-generated key material
- reject requests that omit `csr_pem` when the selected policy path requires a client-provided CSR

### 3.2 Policy Resolution

Policy resolution rules for the MVP:

- if no policy matches the authenticated requester and requested identifiers, reject the request
- if more than one policy matches but all selected runtime choices are identical, choose the most specific policy and record the selected policy name in audit metadata
- if more than one policy matches and they disagree on issuer, challenge type, or key/CSR mode, fail closed and require configuration cleanup instead of guessing
- if the client supplies `issuer_name`, treat it as a constraint that must still be allowed by the selected policy rather than as an unrestricted override
- require every requested identifier in a multi-name order to be allowed by the same selected policy

Identifier-to-policy matching rules:

- treat exact names, wildcard request identifiers, suffix entries, and, when enabled, regex entries as distinct forms during matching
- match request identifiers against policy entries only after request normalization
- use the declared `syntax` field rather than inferring matcher behavior from the `value`
- treat the `suffix` form as the explicit policy form that allows wildcard request identifiers under that zone
- do not satisfy a wildcard request from a plain `exact` host entry
- when a request contains multiple identifiers, evaluate each identifier independently and then require one policy to cover the full set

Wildcard authorization rules for the MVP:

- a requested wildcard identifier such as `*.lab.example.org` may be authorized only by a broader `suffix` entry such as `.lab.example.org`
- an exact apex entry such as `lab.example.org` does not authorize `*.lab.example.org`
- if ACME wildcard issuance is disabled, reject wildcard identifiers even if a broker policy pattern would otherwise match them
- if wildcard issuance is enabled in a later slice, require `dns-01` for wildcard identifiers regardless of any broader challenge preference

Regex policy mode:

- do not include regex matching in the initial MVP
- if regex matching is added later, require explicit configuration to enable it
- allow regex matching only on policy entries that declare `syntax: regex`
- restrict regex patterns to anchored full matches against normalized identifiers
- reject regex flags, partial matches, and engine-specific extensions unless a later document explicitly allows them
- reject regex patterns that fail validation or exceed defined complexity limits
- keep regex-backed policies lower priority than exact matches unless a later document says otherwise

Specificity rules for the MVP:

- prefer exact identifier matches over broader domain patterns
- prefer policies with narrower requester constraints over broader requester constraints
- prefer policies that enumerate fewer allowed domains when both otherwise match the same request
- if two matching policies remain tied after those checks, fail closed instead of relying on file order

## 4. Related Documents

For lifecycle, persistence, and storage behavior, use [`data-model.md`](./data-model.md).

For the optional broker-native HTTP behavior, use [`broker-api-reference.md`](./broker-api-reference.md).
