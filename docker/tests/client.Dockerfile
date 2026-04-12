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

ARG ACMESH_REF=v3.0.5
RUN curl --fail --show-error --silent --location \
    "https://raw.githubusercontent.com/acmesh-official/acme.sh/${ACMESH_REF}/acme.sh" \
    --output /usr/local/bin/acme.sh \
    && chmod 0555 /usr/local/bin/acme.sh

WORKDIR /opt/chain-tests
