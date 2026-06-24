#!/bin/sh
set -e

echo "Starting replica entrypoint..."

# Wait for primary database to be ready
until pg_isready -h postgres -U "${POSTGRES_USER:-cacheflow}"; do
  echo "Waiting for primary database (postgres) to be ready..."
  sleep 1
done

# If the data directory is not initialized yet (doesn't contain PG_VERSION), initialize from primary
if [ ! -s "$PGDATA/PG_VERSION" ]; then
  echo "Initializing replica from primary using pg_basebackup..."
  rm -rf "$PGDATA"/*
  
  # Export password for pg_basebackup
  export PGPASSWORD="${POSTGRES_PASSWORD:-cacheflow}"
  
  # Run pg_basebackup. The -R flag creates standby.signal and configures connection parameters automatically
  pg_basebackup -h postgres -D "$PGDATA" -U "${POSTGRES_USER:-cacheflow}" -Fp -Xs -R -v
  
  echo "Replica initialized successfully."
fi

# Run the standard postgres entrypoint script with the original command (e.g. postgres)
exec docker-entrypoint.sh "$@"
