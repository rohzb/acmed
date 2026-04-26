FROM python:3.12-slim AS runtime-base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOME=/app/data/home

ARG ACMED_SOURCE_DIR=.
ARG ACMED_PLUGIN_DIRS=
ARG ACMESH_REF=3.1.2

# Run as a dedicated non-root user.
RUN groupadd --system --gid 10001 acmed \
    && useradd --system --uid 10001 --gid 10001 --create-home --home-dir /home/acmed --shell /usr/sbin/nologin acmed

WORKDIR /app

# Copy full source workspace so any plugin combination can be selected by build args.
COPY . /tmp/sources

# Install core acmed package.
RUN pip install --no-cache-dir "/tmp/sources/${ACMED_SOURCE_DIR}"

COPY ${ACMED_SOURCE_DIR}/docker/entrypoint.sh /usr/local/bin/acmed-entrypoint
COPY ${ACMED_SOURCE_DIR}/docker/scripts/install-plugin-addons.sh /usr/local/bin/acmed-install-plugin-addons
RUN chmod 0555 /usr/local/bin/acmed-entrypoint /usr/local/bin/acmed-install-plugin-addons

# Install selected plugin Python packages and their addon tooling/extensions.
RUN /usr/local/bin/acmed-install-plugin-addons /tmp/sources "${ACMED_PLUGIN_DIRS}"

# Runtime directories for SQLite, issuer state, and artifacts.
RUN mkdir -p /app/data/orders /app/data/home /app/config \
    && rm -rf /tmp/sources \
    && chown -R acmed:acmed /app /home/acmed

USER acmed:acmed

EXPOSE 8443

ENTRYPOINT ["/usr/local/bin/acmed-entrypoint"]

# Compatibility alias: keep `runtime` available for newer compose presets while
# preserving legacy `runtime-base` CI/build targets.
FROM runtime-base AS runtime
