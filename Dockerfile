FROM python:3.11.13-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN addgroup --system --gid 10001 har \
    && adduser --system --uid 10001 --gid 10001 --home /app har

COPY requirements.txt ./
RUN python -m pip install --upgrade "pip==25.1.1" \
    && python -m pip install --requirement requirements.txt

COPY --chown=har:har shared ./shared
COPY --chown=har:har services ./services

USER har

EXPOSE 8001 8002 8003 8004

CMD ["uvicorn", "services.fusion_service.app:app", "--host", "0.0.0.0", "--port", "8001"]
