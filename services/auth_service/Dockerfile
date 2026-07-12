FROM python:3.11.13-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN addgroup --system --gid 10001 har \
    && adduser --system --uid 10001 --gid 10001 --home /app har

COPY requirements-auth.txt ./
RUN pip install --no-cache-dir --requirement requirements-auth.txt

COPY services/__init__.py ./services/__init__.py
COPY services/auth_service ./services/auth_service
COPY shared ./shared

RUN chown -R har:har /app
USER har

EXPOSE 8005
CMD ["uvicorn", "services.auth_service.app:app", "--host", "0.0.0.0", "--port", "8005"]
