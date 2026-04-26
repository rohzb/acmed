FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install --yes --no-install-recommends \
      ca-certificates \
      certbot \
      curl \
      jq \
      openssl \
      socat \
    && rm -rf /var/lib/apt/lists/*

ARG ACMESH_REF=3.1.2
RUN curl --fail --show-error --silent --location \
    "https://raw.githubusercontent.com/acmesh-official/acme.sh/${ACMESH_REF}/acme.sh" \
    --output /usr/local/bin/acme.sh \
    && chmod 0555 /usr/local/bin/acme.sh

# Run chain tests as a dedicated non-root user.
RUN groupadd --system --gid 10001 chain \
    && useradd --system --uid 10001 --gid 10001 --create-home --home-dir /home/chain --shell /usr/sbin/nologin chain

WORKDIR /opt/chain-tests

USER chain:chain
