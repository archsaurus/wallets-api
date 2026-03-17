#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=/ws${PYTHONPATH:+:$PYTHONPATH}

# красивости
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NO_COLOR='\033[0m'

log() { echo -e "${GREEN}[$(date '+%H:%M:%S')] INFO: $1${NO_COLOR}"; }
warn() { echo -e "${YELLOW}[$(date '+%H:%M:%S')] WARNING: $1${NO_COLOR}" >&2; }
error() { echo -e "${RED}[$(date '+%H:%M:%S')] ERROR: $1${NO_COLOR}" >&2; }


wait_for_postgres() {
	local max_attempts=60
    local attempt=1

	export PGPASSWORD="${POSTGRES_PASSWORD}"

    log "Waiting for PostgreSQL (${POSTGRES_HOST:-db}:${POSTGRES_PORT:-postgres})..."

    while [ $attempt -le $max_attempts ]; do
        if PGPASSWORD=$PGPASSWORD psql \
		 	-h ${POSTGRES_HOST:-db} \
		 	-p ${POSTGRES_PORT:-5432} \
		 	-U ${POSTGRES_USER:-postgres} \
		 	-d ${POSTGRES_DB:-postgres} \
            -c "SELECT 1;" \
		 	-t -q >/dev/null 2>&1; then
            log "PostgreSQL is ready!"
            return 0
        fi

        warn "Attempt $attempt/$max_attempts - DB is not ready yet (checking port ${POSTGRES_PORT})..."

        if [ $((attempt % 10)) -eq 0 ]; then
			log "Network diagnostic:"
			if timeout 1 bash -c "</dev/tcp/db/${POSTGRES_PORT}"; then
				log "Port ${POSTGRES_PORT}: OPEN"
			else
				log "Port ${POSTGRES_PORT}: CLOSED"
			fi
		fi

        sleep 2
        attempt=$((attempt + 1))
    done

    error "PostgreSQL unavailable after ${max_attempts}s"
    error "Check: docker network, postgres logs, DATABASE_URL"
    exit 1
}

run_migrations() {
    if [ "${RUN_MIGRATIONS:-false}" != "true" ]; then
        log "Migrations SKIPPED"
        return 0
    fi

    log "Running Alembic migrations"

	local DB_URL="postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}"

    if [ ! -d "wallet_service/migrations/versions" ] || [ -z "$(ls -A wallet-service/migrations/versions 2>/dev/null)" ]; then
        warn "No migration files found - creating initial migration"
        alembic revision -m "initial_setup" || {
            warn "Autogenerate failed - skipping"
        }
    else
        alembic revision --autogenerate
        alembic upgrade head
    fi

    if "DATABASE_URL=${DB_URL}" alembic current >/dev/null 2>&1; then
        log "DB is up-to-date"
    else
        log "Applying migrations..."
        if DATABASE_URL="$DB_URL" alembic upgrade head; then
            log "Migrations applied successfully"
        else
            error "Migration failed - check alembic_version table"
            warn "Fix: psql -h ${POSTGRES_HOST} -U ${POSTGRES_USER} -d ${POSTGRES_DB} -c 'DROP TABLE IF EXISTS alembic_version;'"
            exit 1
        fi
    fi
}

wait_for_postgres
run_migrations

log "Starting ASGI (${@})"

trap 'log "Shutting down gracefully..."; exit 0' SIGTERM SIGINT

exec "$@"
