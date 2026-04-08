# acmed Policy And Configuration

> [!TIP]
> **TL;DR**
> This document defines the broker configuration shape, policy syntax, matcher semantics, and policy-selection rules.

Use this document as the source of truth for YAML configuration, policy definitions, and policy matching behavior.

## 1. Configuration Shape

Configuration examples should stay aligned with the documented delivery and test strategy:

- start with the broker-native happy path before enabling ACME compatibility
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
  mtls:
    enabled: false

acme:
  enabled: false
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
    type: noop

authorizers:
  - name: subnet-lab
    type: source_subnet
    source_subnets:
      - 10.20.30.0/24

policies:
  - name: lab-broker-happy-path
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

This example is the broker-first baseline with ACME disabled. It is intentionally not the ACME-enabled MVP runtime configuration.

While `acme.enabled` remains `false`, the nested ACME settings shown here should be treated as inactive placeholders for a later ACME-enabled override rather than as active broker-first behavior.

When the implementation reaches the ACME iteration, add a second example or environment-specific override that enables ACME, Pebble-oriented integration settings, and any supported challenge-provider configuration. Do not let the first example imply that wildcard issuance, external ACME backends, or production Let’s Encrypt integration are part of the initial milestone.

For the ACME MVP, the enabled ACME configuration should:

- advertise both `http-01` and `dns-01`
- require External Account Binding for account creation
- keep wildcard support disabled unless the full `dns-01` wildcard path is implemented end to end

## 2. Policy Matcher Syntax

For the broker-first MVP and later extensions, `allowed_domains` entries should declare their matching syntax explicitly.

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

Supported `syntax` values:

- `exact`
- `suffix`
- `regex`

Broker-first MVP support:

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

## 3. Policy Selection

### 3.1 Request Normalization And Identity

Before persisting a broker-native order:

- authenticate the requester and derive one stable `requester_id`
- normalize all DNS names before policy evaluation
- reject empty identifier sets, malformed names, duplicate names, or a `common_name` that is not present in `dns_names`
- resolve exactly one effective policy for the request

Requester identity rules for the broker-first MVP:

- derive `requester_id` from the authenticated credential rather than from client-supplied request fields
- when API tokens are used, bind `requester_id` to the token's configured subject or principal name
- when mTLS is used, bind `requester_id` to the verified client certificate identity after any configured mapping step
- never allow the requester to override `requester_id` in the JSON payload

### 3.2 Policy Resolution

Policy resolution rules for the broker-first MVP:

- if no policy matches the authenticated requester and requested identifiers, reject the request
- if more than one policy matches but all selected runtime choices are identical, choose the most specific policy and record the selected policy name in audit metadata
- if more than one policy matches and they disagree on issuer, challenge type, or key/CSR mode, fail closed and require configuration cleanup instead of guessing
- if the client supplies `issuer_name`, treat it as a constraint that must still be allowed by the selected policy rather than as an unrestricted override
- require every requested identifier in a multi-name order to be allowed by the same selected policy

Identifier-to-policy matching rules:

- treat exact names, wildcard request identifiers, suffix entries, and regex entries as distinct forms during matching
- match request identifiers against policy entries only after request normalization
- use the declared `syntax` field rather than inferring matcher behavior from the `value`
- in the broker-first MVP, treat the `suffix` form as the explicit policy form that allows wildcard request identifiers under that zone
- do not satisfy a wildcard request from a plain `exact` host entry
- when a request contains multiple identifiers, evaluate each identifier independently and then require one policy to cover the full set

Wildcard authorization rules for the broker-first MVP:

- a requested wildcard identifier such as `*.lab.example.org` may be authorized only by a broader `suffix` entry such as `.lab.example.org`
- an exact apex entry such as `lab.example.org` does not authorize `*.lab.example.org`
- if ACME wildcard issuance is disabled, reject wildcard identifiers even if a broker policy pattern would otherwise match them
- if ACME wildcard issuance is enabled later, require `dns-01` for wildcard identifiers regardless of any broader challenge preference

Regex policy mode:

- do not include regex matching in the broker-first MVP
- if regex matching is added later, require explicit configuration to enable it
- allow regex matching only on policy entries that declare `syntax: regex`
- restrict regex patterns to anchored full matches against normalized identifiers
- reject regex flags, partial matches, and engine-specific extensions unless a later document explicitly allows them
- reject regex patterns that fail validation or exceed defined complexity limits
- keep regex-backed policies lower priority than exact matches unless a later document says otherwise

Specificity rules for the broker-first MVP:

- prefer exact identifier matches over broader domain patterns
- prefer policies with narrower requester constraints over broader requester constraints
- prefer policies that enumerate fewer allowed domains when both otherwise match the same request
- if two matching policies remain tied after those checks, fail closed instead of relying on file order
