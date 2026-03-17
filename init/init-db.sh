#!/bin/bash
set -e



RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NO_COLOR='\033[0m'

log() { echo -e "${GREEN}[$(date '+%H:%M:%S')] INFO: $1${NO_COLOR}"; }
warn() { echo -e "${YELLOW}[$(date '+%H:%M:%S')] WARNING: $1${NO_COLOR}" >&2; }
error() { echo -e "${RED}[$(date '+%H:%M:%S')] ERROR: $1${NO_COLOR}" >&2; }



psql -v ON_ERROR_STOP=1 --username "postgres" <<-EOSQL
DO \$\$ 
BEGIN
   IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '$POSTGRES_USER') THEN
      CREATE ROLE "$POSTGRES_USER" WITH LOGIN PASSWORD '$POSTGRES_PASSWORD';
      -- ALTER DATABASE "$POSTGRES_DB" OWNER TO "$POSTGRES_USER";
   END IF;
END
\$\$;

DO \$\$ 
BEGIN
   IF NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = '$POSTGRES_DB') THEN
      EXECUTE format('CREATE DATABASE %I OWNER %I', '$POSTGRES_DB', '$POSTGRES_USER');
   END IF;
END
\$\$;
EOSQL
