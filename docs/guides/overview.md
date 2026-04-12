# acmed Overview

For compact machine-oriented contracts, see [`../models/README.md`](../models/README.md).

`acmed` is an ACME-first broker service for internal infrastructure. It sits between internal clients and issuer tooling, so policy and request handling are centralized instead of being reimplemented on every host.

In practice, `acmed` handles requester identity, policy checks, optional internal proof, and order state, then delegates actual challenge/issuance work to issuer adapters such as `acme.sh` or `certbot`. It stays intentionally thin: brokering and orchestration in one place, issuer-specific mechanics in the adapters.

The key boundary in this project is that issuer capability is not requester permission. Broad DNS or CA credentials stay with issuer profiles, while policy decides who can request which names and through which issuer. That is what keeps internal automation practical without turning every requester into a privileged CA client.

For v1, the scope is intentionally small:

- ACME-first interface
- asynchronous order lifecycle with persistent state
- policy + authorizer + proof-handler boundaries
- issuer adapters (including a real issuer path, not only mock)
- audit trails and practical test coverage

The broker-native API can be added later, but it stays secondary to the ACME path and should not reshape the core model.
