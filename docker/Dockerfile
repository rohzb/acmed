FROM python:3.12-slim AS runtime-base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Run as a dedicated non-root user.
RUN groupadd --system --gid 10001 acmed \
    && useradd --system --uid 10001 --gid 10001 --create-home --home-dir /home/acmed --shell /usr/sbin/nologin acmed

WORKDIR /app

# Install acmed package from local source.
COPY pyproject.toml /app/pyproject.toml
COPY src /app/src
RUN pip install --no-cache-dir .

# Runtime directories for SQLite and artifacts.
RUN mkdir -p /app/data/orders /app/config \
    && chown -R acmed:acmed /app /home/acmed

COPY docker/entrypoint.sh /usr/local/bin/acmed-entrypoint
RUN chmod 0555 /usr/local/bin/acmed-entrypoint

USER acmed:acmed

EXPOSE 8443

ENTRYPOINT ["/usr/local/bin/acmed-entrypoint"]

FROM runtime-base AS runtime-acmesh

USER root

RUN apt-get update \
    && apt-get install --yes --no-install-recommends ca-certificates curl openssl socat \
    && rm -rf /var/lib/apt/lists/*

ARG ACMESH_REF=v3.0.5
RUN curl --fail --show-error --silent --location \
    "https://raw.githubusercontent.com/acmesh-official/acme.sh/${ACMESH_REF}/acme.sh" \
    --output /usr/local/bin/acme.sh \
    && chmod 0555 /usr/local/bin/acme.sh

USER acmed:acmed

FROM runtime-base AS runtime-certbot

USER root

RUN apt-get update \
    && apt-get install --yes --no-install-recommends certbot \
    && rm -rf /var/lib/apt/lists/*

USER acmed:acmed

FROM runtime-base AS runtime-issuers

USER root

RUN apt-get update \
    && apt-get install --yes --no-install-recommends ca-certificates certbot curl openssl socat \
    && rm -rf /var/lib/apt/lists/*

ARG ACMESH_REF=v3.0.5
RUN curl --fail --show-error --silent --location \
    "https://raw.githubusercontent.com/acmesh-official/acme.sh/${ACMESH_REF}/acme.sh" \
    --output /usr/local/bin/acme.sh \
    && chmod 0555 /usr/local/bin/acme.sh

USER acmed:acmed
