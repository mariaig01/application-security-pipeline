FROM python:3.12-alpine@sha256:c5ba3deef00c7758561a0f03c26f44f10589263d40e732b8748e0d1f38f6dd89 AS python-base
# This service supports PostgreSQL only. Remove the unused SQLite binding and
# its package, retaining the package-manager inventory for every installed library.
RUN find /usr/local/lib/python3.12/lib-dynload -maxdepth 1 -name '_sqlite3*.so' -delete \
    && runtime_deps="$(apk info --depends .python-rundeps | sed -n '/^so:/p' | grep -v '^so:libsqlite3.so.0$')" \
    && apk add --no-cache --virtual .app-rundeps $runtime_deps \
    && apk del .python-rundeps \
    && apk add --no-cache krb5-libs=1.22.3-r0

FROM python-base AS dependencies
WORKDIR /build
RUN pip install --no-cache-dir uv==0.12.16
COPY pyproject.toml uv.lock ./
RUN UV_PROJECT_ENVIRONMENT=/opt/venv uv sync --frozen --no-dev --no-install-project --no-cache

FROM dependencies AS test-dependencies
RUN UV_PROJECT_ENVIRONMENT=/opt/venv uv sync --frozen --no-install-project --no-cache

FROM python-base AS app-base
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
RUN addgroup -g 10001 appsec \
    && adduser -D -u 10001 -G appsec -s /sbin/nologin appsec
WORKDIR /app
COPY --from=dependencies /opt/venv /opt/venv
COPY appsec_pipeline ./appsec_pipeline
COPY migrations ./migrations
COPY alembic.ini ./
USER 10001:10001
EXPOSE 8000
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "30", "--worker-tmp-dir", "/tmp", "appsec_pipeline:create_app()"]

FROM app-base AS test
COPY --from=test-dependencies /opt/venv /opt/venv
COPY tests ./tests
COPY scripts ./scripts
COPY security ./security
COPY pyproject.toml ./
CMD ["sh", "-c", "ruff check --no-cache . && ruff format --check --no-cache . && pytest -q -p no:cacheprovider"]

FROM app-base AS runtime
