FROM python:3.14-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /ws

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
&& rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --upgrade pip && \
    /opt/venv/bin/pip install --no-cache-dir -r requirements.txt


FROM python:3.14-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

ARG UID=10001
RUN adduser \
    --disabled-password \
    --gecos "" \
    --home /home/archsaurus \
    --shell /sbin/nologin \
    --uid "$UID" \
    archsaurus


RUN apt-get update && apt-get install -y --no-install-recommends postgresql-client


WORKDIR /ws

COPY --from=builder /opt/venv /opt/venv

COPY --chown=archsaurus:archsaurus wallet_service ./wallet_service
COPY --chown=archsaurus:archsaurus alembic.ini .
COPY --chown=archsaurus:archsaurus ./entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh


EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

USER archsaurus

ENTRYPOINT ["/entrypoint.sh"]

CMD ["uvicorn", "wallet_service.application.main:wallet_application", \
    "--host", "0.0.0.0", "--port", "8000", "--workers", "12", \
    "--limit-max-requests", "10000", "--limit-max-requests-jitter", "1000"]
