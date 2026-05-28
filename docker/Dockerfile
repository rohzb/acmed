FROM python:3.12-slim AS runtime-base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOME=/app/data/home \
    ACMED_ACMESH_HOME=/app/data/acmesh \
    ACMED_ACMESH_DNSAPI_DIR=/opt/acmed/acme.sh/dnsapi

ARG ACMED_SOURCE_DIR=.
ARG ACMESH_REF=3.1.2

# Run as a dedicated non-root user.
RUN groupadd --system --gid 10001 acmed \
    && useradd --system --uid 10001 --gid 10001 --create-home --home-dir /home/acmed --shell /usr/sbin/nologin acmed

WORKDIR /app

# Install core acmed package from the selected source directory.
COPY ${ACMED_SOURCE_DIR} /tmp/acmed-source
RUN pip install --no-cache-dir /tmp/acmed-source

COPY ${ACMED_SOURCE_DIR}/docker/entrypoint.sh /usr/local/bin/acmed-entrypoint
COPY ${ACMED_SOURCE_DIR}/docker/scripts/install-issuer-tools.sh /usr/local/bin/acmed-install-issuer-tools
RUN chmod 0555 /usr/local/bin/acmed-entrypoint /usr/local/bin/acmed-install-issuer-tools

# Install issuer CLIs directly into the core runtime image.
RUN /usr/local/bin/acmed-install-issuer-tools "${ACMESH_REF}"

# Runtime directories for SQLite, issuer state, and artifacts.
RUN mkdir -p /app/data/orders /app/data/home /app/data/acmesh /app/config /opt/acmed \
    && rm -rf /tmp/acmed-source \
    && chown -R acmed:acmed /app /home/acmed /opt/acmed

USER acmed:acmed

EXPOSE 8443

ENTRYPOINT ["/usr/local/bin/acmed-entrypoint"]

# Compatibility alias: keep `runtime` available for existing compose presets.
FROM runtime-base AS runtime
