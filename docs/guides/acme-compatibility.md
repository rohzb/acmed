# acmed ACME Compatibility Notes

This file is for practical compatibility testing notes.
If you need the actual ACME contract, use [`acme-api.md`](../reference/acme-api.md).

## 1. Purpose

This doc focuses on:

- issuer-tool validation notes
- optional client-oriented smoke-test examples
- compatibility validation notes
- practical reminders about how `certbot` and `acme.sh` fit into the overall design

Treat this as test guidance, not the protocol spec.

## 2. Compatibility Rules

- point clients at the ACME directory URL
- advertise only the ACME features actually implemented
- do not claim compatibility with a named client or issuer wrapper unless that path has been tested
- keep the documented supported feature set synchronized with the real implementation
- use Pebble or another deterministic CA for local external-issuer testing where possible
- require the ACME surface to advertise only the ACME features truly implemented

If this doc and [`acme-api.md`](../reference/acme-api.md) differ, follow the API reference.

Preferred testing environments:

- use Pebble as the default local ACME test server for automated issuer integration and ACME smoke tests
- use Let’s Encrypt staging only as optional external verification

Pebble setup assumption:

- the local ACME test environment should expose a normal ACME directory URL shape so `certbot` and `acme.sh` can be pointed at it the same way they would be pointed at a real ACME server

## 3. Client Smoke-Test Examples

These examples are illustrative smoke-test targets, not production runbooks.

These examples intentionally skip exact External Account Binding flags because those vary across client versions. The real test workflow should still cover EAB.

### certbot example

```bash
certbot certonly \
  --server https://<host>/acme/directory \
  --manual \
  --preferred-challenges dns \
  -d example.org
```

If the ACME surface documents `http-01` support, the real smoke test should cover an `http-01` path, for example with a manual or test harness flow that provisions the token response material expected by the server.

### acme.sh example

```bash
acme.sh --issue \
  --server https://<host>/acme/directory \
  --dns \
  -d example.org
```

The real smoke test suite should cover every challenge type the ACME surface advertises rather than assuming both `dns-01` and `http-01` are always in scope.

The exact smoke-test command may vary by challenge method, but the implementation should support the normal directory-URL based client model.

## 4. What To Validate

For both `certbot` and `acme.sh`, validate at least:

- directory discovery
- nonce handling
- account creation with External Account Binding
- order creation
- challenge acknowledgement
- finalize flow
- certificate download

Also validate:

- across the named-client smoke-test set, every advertised ACME challenge path
- failures are reported in ACME-compatible ways
- unsupported features are not advertised
- wildcard behavior matches the documented supported challenge set

## 5. Staging Verification Notes

Let’s Encrypt staging can be useful for additional confidence because it behaves like a real external ACME environment, but it should not be the default automated dependency.

Use staging when:

- preparing for release
- confirming behavior beyond the local Pebble environment
- manually checking interoperability in a more realistic network setting

Do not make normal automated test runs depend on staging availability.

## 6. References

- [`acme-api.md`](../reference/acme-api.md)
- RFC 8555: https://datatracker.ietf.org/doc/html/rfc8555
- Certbot usage docs: https://eff-certbot.readthedocs.io/en/latest/using.html
- acme.sh server parameter notes: https://github-wiki-see.page/m/acmesh-official/acme.sh/wiki/Server
- Let’s Encrypt staging environment: https://letsencrypt.org/docs/staging-environment/
- Pebble: https://github.com/letsencrypt/pebble
