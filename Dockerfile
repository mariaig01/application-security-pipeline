FROM python:3.12.14-slim-bookworm@sha256:392307d22300de8b5986851a12d9176dfc0fc073e65bf6523ebd7dcbeb23564e AS dependencies
WORKDIR /build
RUN pip install --no-cache-dir uv==0.12.16
COPY pyproject.toml uv.lock ./
RUN UV_PROJECT_ENVIRONMENT=/opt/venv uv sync --frozen --no-dev --no-install-project --no-cache

FROM dependencies AS test-dependencies
RUN UV_PROJECT_ENVIRONMENT=/opt/venv uv sync --frozen --no-install-project --no-cache

FROM python:3.12.14-slim-bookworm@sha256:392307d22300de8b5986851a12d9176dfc0fc073e65bf6523ebd7dcbeb23564e AS app-base
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
RUN useradd --uid 10001 --create-home --shell /usr/sbin/nologin appsec
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
COPY pyproject.toml ./
CMD ["sh", "-c", "ruff check --no-cache . && ruff format --check --no-cache . && pytest -q -p no:cacheprovider"]

FROM app-base AS runtime
