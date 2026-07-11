FROM ghcr.io/astral-sh/uv:0.11.21 AS uv

FROM python:3.11.13-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

RUN apt-get update \
    && apt-get install --yes --no-install-recommends libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

RUN addgroup --system --gid 10001 har \
    && adduser --system --uid 10001 --gid 10001 --home /app har

COPY --from=uv /uv /uvx /bin/
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY --chown=har:har shared ./shared
COPY --chown=har:har services ./services
COPY --chown=har:har simulator ./simulator

USER har

EXPOSE 8001 8002 8003 8004

CMD ["uvicorn", "services.fusion_service.app:app", "--host", "0.0.0.0", "--port", "8001"]
