# Certbot + Pre-Authorization Tutorial

## 1. Overview

Use this tutorial when:

- `acmed` is running (for example at `acme.amgro.de:8443`)
- you want to request a certificate from a different machine with `certbot`
- you want pre-authorization to be explicit in policy

Pre-authorization in `acmed` is policy authorizer enforcement during ACME `newOrder`.

## 2. Server Setup

### 2.1 If you use Docker, pick a starter config first

Copy one profile to the active Docker config path:

```bash
cp docker/config/config.allow-all.yml docker/config/config.yml
```

or:

```bash
cp docker/config/config.source-subnet-local.yml docker/config/config.yml
```

or:

```bash
cp docker/config/config.trusted-bypass-local.yml docker/config/config.yml
```

Then continue with the matching policy mode notes below.

### 2.2 Pick one pre-authorization mode

Use one of these authorizer setups in your active config (`docker/config/config.yml`).

#### Option A: no-auth policy path (`allow_all`)

```yaml
authorizers:
  - name: allow-all
    type: allow_all

policies:
  - name: certbot-test
    requester_match:
      authorizers: [allow-all]
    allowed_domains:
      - syntax: suffix
        value: .lab.example.org
    allowed_issuers: [mock]
    proof_handler: no-proof
    csr_mode: either
```

#### Option B: source-IP pre-authorization (`source_subnet`)

```yaml
authorizers:
  - name: local-private-subnets
    type: source_subnet
    source_subnets:
      - 10.0.0.0/8
      - 172.16.0.0/12
      - 192.168.0.0/16
      - 127.0.0.0/8

policies:
  - name: certbot-test
    requester_match:
      authorizers: [local-private-subnets]
    allowed_domains:
      - syntax: suffix
        value: .lab.example.org
    allowed_issuers: [mock]
    proof_handler: no-proof
    csr_mode: either
```

#### Option C: trusted policy bypass for ACME challenge validation (development only)

Use this only in trusted local/lab environments. Keep `server.development_mode: true`.

```yaml
policies:
  - name: certbot-test
    requester_match:
      authorizers: [local-private-subnets]
    allowed_domains:
      - syntax: suffix
        value: .lab.example.org
    allowed_issuers: [mock]
    proof_handler: no-proof
    csr_mode: either
    challenge_validation_mode: trusted_bypass
```

With this mode, challenge acknowledgement can be accepted without external `http-01` probing.

### 2.3 ACME settings for first test

```yaml
acme:
  enabled: true
  directory_path: /acme/directory
  require_eab: false
  allow_wildcards: false
  supported_challenge_types: [http-01]
```

`require_eab: false` keeps first enrollment simple.

### 2.4 Restart `acmed`

If you use Docker Compose:

```bash
docker compose -f docker/docker-compose.yml --env-file docker/.env up -d --build
```

## 3. Certbot Client Setup

Run these steps on the other machine.

### 3.1 Install certbot

Use your OS package manager or Python tooling. Then check:

```bash
certbot --version
```

### 3.2 Prepare local certbot working directories

```bash
mkdir -p "$HOME/certbot-acmed/config" "$HOME/certbot-acmed/work" "$HOME/certbot-acmed/logs"
```

## 4. Request A Test Certificate

Use a domain that:

- matches your policy (for example `host1.lab.example.org`)
- resolves to the certbot machine for `http-01`
- can be reached by the `acmed` host on TCP 80

Run:

```bash
certbot certonly \
  --standalone \
  --preferred-challenges http \
  --http-01-port 80 \
  --server http://acme.amgro.de:8443/acme/directory \
  --no-verify-ssl \
  --agree-tos \
  --register-unsafely-without-email \
  --config-dir "$HOME/certbot-acmed/config" \
  --work-dir "$HOME/certbot-acmed/work" \
  --logs-dir "$HOME/certbot-acmed/logs" \
  -d host1.lab.example.org
```

`--standalone` runs a temporary HTTP server in certbot itself for `http-01`.
Make sure port `80` on the certbot machine is free and reachable from the `acmed` host.

If you use `challenge_validation_mode: trusted_bypass`, certbot still performs normal ACME steps, but `acmed` may mark the challenge valid without external fetch checks.

## 5. Verify Results

### 5.1 Certbot output

Look for a successful issuance message in certbot output.

### 5.2 Local certificate files

```bash
ls -la "$HOME/certbot-acmed/config/live/"
```

### 5.3 `acmed` artifacts

On the `acmed` host:

```bash
find data/orders -maxdepth 3 -type f | sort
```

## 6. Optional: Turn On EAB Later

If you later set:

```yaml
acme:
  require_eab: true
  eab_credentials:
    - kid: certbot-client-1
      secret_env: ACMED_EAB_CERTBOT_1
```

then restart `acmed` and add certbot EAB flags:

```bash
--eab-kid certbot-client-1 --eab-hmac-key "<EAB_HMAC_KEY>"
```

## 7. Troubleshooting

### 7.1 `403` on `newOrder`

Likely causes:

- certbot source IP does not match `source_subnet`
- requested DNS name is outside `allowed_domains`
- policy does not include a matching authorizer name

### 7.2 Challenge becomes `invalid`

Likely causes:

- domain does not resolve to the certbot machine
- challenge file is not reachable on TCP 80
- challenge token content mismatch

### 7.3 TLS verification errors to ACME directory

For local HTTP/self-signed testing, keep:

```bash
--no-verify-ssl
```

For production, run `acmed` with trusted TLS and remove that flag.

## 8. Related Documents

- [`acme-api.md`](../reference/acme-api.md)
- [`configuration.md`](../reference/configuration.md)
- [`acme-compatibility.md`](../guides/acme-compatibility.md)
- [`../docker/README.md`](../../docker/README.md)
