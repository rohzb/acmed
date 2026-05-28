#!/usr/bin/env sh
# Install issuer CLI tooling (acme.sh and certbot DNS plugins).
# Usage: install-issuer-tools.sh [acmesh-ref]
# Author: Ruslan Ovsyannikov <rovsyannikov@gmail.com>
# License: MIT

set -eu

ACMESH_REF="${1:-3.1.2}"

apt-get update
apt-get install --yes --no-install-recommends \
  ca-certificates \
  curl \
  tar \
  certbot \
  python3-certbot-dns-cloudflare \
  python3-certbot-dns-digitalocean \
  python3-certbot-dns-dnsimple \
  python3-certbot-dns-dnsmadeeasy \
  python3-certbot-dns-gehirn \
  python3-certbot-dns-google \
  python3-certbot-dns-linode \
  python3-certbot-dns-luadns \
  python3-certbot-dns-nsone \
  python3-certbot-dns-ovh \
  python3-certbot-dns-rfc2136 \
  python3-certbot-dns-route53 \
  python3-certbot-dns-sakuracloud
rm -rf /var/lib/apt/lists/*

curl --fail --show-error --silent --location \
  "https://raw.githubusercontent.com/acmesh-official/acme.sh/${ACMESH_REF}/acme.sh" \
  --output /usr/local/bin/acme.sh
chmod 0555 /usr/local/bin/acme.sh

tmp_dir="$(mktemp -d)"
archive_url="https://github.com/acmesh-official/acme.sh/archive/refs/tags/${ACMESH_REF}.tar.gz"
if ! curl --fail --show-error --silent --location \
  "${archive_url}" \
  --output "${tmp_dir}/acme.sh.tar.gz"; then
  archive_url="https://github.com/acmesh-official/acme.sh/archive/refs/heads/${ACMESH_REF}.tar.gz"
  curl --fail --show-error --silent --location \
    "${archive_url}" \
    --output "${tmp_dir}/acme.sh.tar.gz"
fi

tar -xzf "${tmp_dir}/acme.sh.tar.gz" -C "${tmp_dir}"
mkdir -p /usr/local/share/acme.sh
cp -a "${tmp_dir}"/acme.sh-*/dnsapi /usr/local/share/acme.sh/dnsapi
rm -rf "${tmp_dir}"
