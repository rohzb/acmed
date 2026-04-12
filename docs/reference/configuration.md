# acmed Policy And Configuration

For schema-style automation input, see [`../models/config-schema.md`](../models/config-schema.md).

## 1. Configuration Shape

Configuration examples should stay aligned with the documented delivery and test strategy:

- treat ACME as the primary external interface for the v1
- use local, deterministic settings for routine automated testing
- prefer Pebble-oriented settings for local issuer integration runs
- treat external public CA staging as optional verification rather than the default test target

```yaml
server:
  host: 0.0.0.0
  port: 8443
  tls_enabled: true

identity:
  api_tokens:
    enabled: true
    tokens:
      - token_id: app-host-1
        subject: host1.lab.example.org
        secret_env: ACMED_TOKEN_APP_HOST_1
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

storage:
  sqlite_path: data/acmed.db
  artifacts_root: data/orders

workers:
  poll_interval_seconds: 2
  max_parallel_orders: 4

issuers:
  - name: pebble-acmesh-dns
    type: acme_sh
    executable: /usr/bin/acme.sh
    ca_directory_url: https://pebble:14000/dir
    challenge_mode: dns-01
    plugin_name: dns_cf
    credential_env:
      - CF_Token
    capability_scope:
      - syntax: suffix
        value: .lab.example.org

  - name: le-certbot-dns
    type: certbot
    executable: /usr/bin/certbot
    ca_directory_url: https://acme-staging-v02.api.letsencrypt.org/directory
    challenge_mode: dns-01
    plugin_name: dns-route53
    credential_env:
      - AWS_ACCESS_KEY_ID
      - AWS_SECRET_ACCESS_KEY
    capability_scope:
      - syntax: suffix
        value: .example.org

  - name: mock
    type: mock

proof_handlers:
  - name: no-proof
    type: none

  - name: inventory-assertion
    type: inventory_assertion
    inventory_source: local

authorizers:
  - name: subnet-lab
    type: source_subnet
    source_subnets:
      - 10.20.30.0/24

policies:
  - name: lab-hosts
    requester_match:
      authorizers:
        - subnet-lab
    allowed_domains:
      - syntax: exact
        value: host1.lab.example.org
      - syntax: exact
        value: host2.lab.example.org
    allowed_issuers:
      - pebble-acmesh-dns
      - mock
    proof_handler: inventory-assertion
    challenge_validation_mode: strict

  - name: shared-zone-automation
    requester_match:
      authorizers:
        - subnet-lab
    allowed_domains:
      - syntax: suffix
        value: .apps.lab.example.org
    allowed_issuers:
      - pebble-acmesh-dns
    proof_handler: no-proof
    challenge_validation_mode: strict
```

This example shows the intended trust split:

- internal requesters authenticate to `acmed`
- policies decide which names they may request
- policies decide which issuer profiles they may invoke
- issuer profiles hold the broader validation plugins and credentials needed to satisfy the real external challenge flow

The same runtime may later expose a broker-native API, but that does not change the core policy model and should not drive the v1 implementation.

### 1.1 Interface boundary in configuration

Keep the configuration split conceptually even when one process hosts multiple surfaces:

- `acme.*` controls the primary ACME-facing behavior
- `identity.*` and `access.*` primarily control admin behavior and any later broker API
- `issuers`, `proof_handlers`, `authorizers`, `policies`, `storage`, and `workers` belong to the shared broker-style core
- do not model external CA challenge plugins as requester-facing policy features

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

Broker, ACME enrollment, and admin identity rules:

- support API-token authentication for the admin surface and any later broker API
- treat each configured API token as one stable requester subject
- resolve `requester_id` from the token's configured `subject`
- read token secret material from an environment variable named by `secret_env` rather than from inline YAML secret text
- reject startup if two enabled tokens resolve to the same `token_id` or same `subject`
- if the ACME surface is enabled, use ACME account authentication and any documented enrollment rules for the client-facing ACME flow

mTLS configuration rules:

- allow `mtls.enabled: false` for the default local path
- require `trusted_client_ca_file` when `mtls.enabled: true`
- if mTLS subject mappings are configured, apply them after certificate verification and before policy lookup
- reject startup if a mapping would resolve to an empty or duplicate requester subject

Admin configuration rules:

- treat `access.admin_subjects` as the small explicit allow-list for admin endpoints
- require the authenticated subject to appear in `access.admin_subjects` before serving `/api/v1/admin/*`
- do not derive admin privilege from policy matches or requested identifiers

## 2. Issuer Profiles

An issuer profile describes a named external fulfillment path.

Each issuer profile should declare:

- the adapter type such as `acme_sh`, `certbot`, or `mock`
- the fixed executable path when applicable
- the target CA directory URL or equivalent endpoint configuration
- the external validation mode such as `dns-01` or `http-01`
- the external plugin name when one is required
- the credential environment variables needed by that issuer
- the broad capability scope that the issuer can technically validate

Issuer-profile rules:

- treat issuer profiles as privileged operational objects, not as requester-supplied plugin choices
- keep executable paths explicit
- keep credential sources outside YAML secret literals
- record capability scope so operators can review the real blast radius of each issuer profile
- reject startup if an issuer profile references an unsupported adapter type or missing executable path
- reject startup if two issuer profiles share the same name

Capability-scope meaning:

- `capability_scope` describes what the issuer could technically validate with its configured credentials
- policy still decides what a requester may actually request through that issuer
- requester authorization must always be narrower than or equal to the selected policy, even when issuer capability is much broader

## 3. Policy Matcher Syntax

For the v1 and later extensions, `allowed_domains` entries should declare their matching syntax explicitly.

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

## 4. Policy Selection

### 4.1 Request Normalization And Identity

Before persisting an order from any external interface:

- authenticate the requester and derive one stable `requester_id`
- normalize all DNS names before policy evaluation
- reject empty identifier sets, malformed names, duplicate names, or a `common_name` that is not present in `dns_names`
- resolve exactly one effective policy for the request

Requester identity rules for the v1:

- derive `requester_id` from the authenticated credential rather than from client-supplied request fields
- for broker API requests, bind `requester_id` to the token's configured subject or verified mTLS identity after any configured mapping step
- if a later inbound ACME surface exists, bind `requester_id` to the ACME account identity or equivalent stable account-key identifier
- never allow the requester to override `requester_id` in the request payload

Identifier normalization rules apply the same way across all interfaces even when the authentication model differs.

Client input mode rules:

- if the request includes `csr_pem`, treat it as a request for `client_provided` CSR mode
- if the request omits `csr_pem`, treat it as a request for `service_generated` CSR mode
- accept the request only if the selected policy and issuer path support that mode
- reject requests that include `csr_pem` but select a policy path that requires service-generated key material
- reject requests that omit `csr_pem` when the selected policy path requires a client-provided CSR

### 4.2 Policy Resolution

Policy resolution rules for the v1:

- if no policy matches the authenticated requester and requested identifiers, reject the request
- if more than one policy matches but all selected runtime choices are identical, choose the most specific policy and record the selected policy name in audit metadata
- if more than one policy matches and they disagree on issuer access, proof handling, key/CSR mode, or challenge validation mode, fail closed and require configuration cleanup instead of guessing
- if the client supplies `issuer_name`, treat it as a constraint that must still be allowed by the selected policy rather than as an unrestricted override
- require every requested identifier in a multi-name order to be allowed by the same selected policy

Issuer-selection rules:

- every policy must name one or more `allowed_issuers`
- every policy must name exactly one `proof_handler`
- the selected issuer must be one of the policy's `allowed_issuers`
- startup validation should reject a policy that references an unknown issuer or proof handler
- startup validation should reject a policy that expands requester access implicitly through an unknown default issuer

### 4.4 Challenge Validation Mode

Each policy may define:

- `challenge_validation_mode: strict` (default)
- `challenge_validation_mode: trusted_bypass`

`strict` mode behavior:

- ACME challenge acknowledgements run normal challenge validation (`http-01`, `dns-01`, or `tls-alpn-01`)
- challenge and authorization state is updated from the real validation result

`trusted_bypass` mode behavior:

- challenge acknowledgement marks the challenge as valid without external challenge probing
- intended only for trusted development/lab paths

Safety rules:

- `trusted_bypass` must be rejected at startup unless `server.development_mode: true`
- keep `trusted_bypass` policies narrow and protected by explicit authorizers such as `source_subnet`
- use `strict` mode for normal and production-like ACME compatibility testing

Identifier-to-policy matching rules:

- treat exact names, suffix entries, and, when enabled, regex entries as distinct forms during matching
- match request identifiers against policy entries only after request normalization
- use the declared `syntax` field rather than inferring matcher behavior from the `value`
- when a request contains multiple identifiers, evaluate each identifier independently and then require one policy to cover the full set

### 4.3 Trust split between requesters and issuers

The central safety property is that issuer capability is not requester permission.

Required rules:

- a broad DNS-capable issuer profile may exist even when most requesters may use only a narrow subset of names
- do not infer requester permission from the issuer profile's `capability_scope`
- do not expose issuer plugin details or issuer credentials in requester-facing APIs
- keep policy review focused on the pair of `allowed_domains` and `allowed_issuers`
- treat `no-proof` as a high-trust path that must be explicit and auditable
