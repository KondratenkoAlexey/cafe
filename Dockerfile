# Multi-stage build for Raspberry Pi (arm64) and local Docker.
FROM ghcr.io/astral-sh/uv:python3.12-trixie-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_DEV=1 \
    UV_PYTHON_DOWNLOADS=0

WORKDIR /app

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project

COPY . /app

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-project


FROM python:3.12-slim-trixie

RUN groupadd --system --gid 999 cafe \
 && useradd --system --gid 999 --uid 999 --create-home cafe \
 && apt-get update \
 && apt-get install -y --no-install-recommends libpq5 gosu \
 && rm -rf /var/lib/apt/lists/*

COPY --from=builder --chown=cafe:cafe /app /app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY deploy/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh \
 && mkdir -p /app/media /app/staticfiles \
 && chown -R cafe:cafe /app/media /app/staticfiles

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--threads", "2", "--timeout", "60"]
