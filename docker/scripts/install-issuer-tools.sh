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
  certbot

# Some certbot DNS plugin packages are distro-specific and may be absent on
# slim base images. Install only plugins that exist in the current apt index.
CERTBOT_DNS_CANDIDATES="
python3-certbot-dns-cloudflare
python3-certbot-dns-digitalocean
python3-certbot-dns-dnsimple
python3-certbot-dns-dnsmadeeasy
python3-certbot-dns-gehirn
python3-certbot-dns-google
python3-certbot-dns-linode
python3-certbot-dns-luadns
python3-certbot-dns-nsone
python3-certbot-dns-ovh
python3-certbot-dns-rfc2136
python3-certbot-dns-route53
python3-certbot-dns-sakuracloud
"

available_plugins=""
for pkg in ${CERTBOT_DNS_CANDIDATES}; do
  if apt-cache show "$pkg" >/dev/null 2>&1; then
    available_plugins="${available_plugins} ${pkg}"
  fi
done

if [ -n "${available_plugins# }" ]; then
  # Intentional word splitting: apt-get expects package names as separate args.
  # shellcheck disable=SC2086
  apt-get install --yes --no-install-recommends ${available_plugins}
fi

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

# Install dnsapi hooks into a deterministic ACMED-owned image path.
mkdir -p /opt/acmed/acme.sh
cp -a "${tmp_dir}"/acme.sh-*/dnsapi /opt/acmed/acme.sh/dnsapi

for home_base in /app/data/home /home/acmed; do
  mkdir -p "${home_base}/.acme.sh"
  rm -rf "${home_base}/.acme.sh/dnsapi"
  cp -a /opt/acmed/acme.sh/dnsapi "${home_base}/.acme.sh/dnsapi"
done

# Runtime user in Dockerfile is uid/gid 10001.
chown -R 10001:10001 /app/data/home /home/acmed /opt/acmed

rm -rf "${tmp_dir}"
