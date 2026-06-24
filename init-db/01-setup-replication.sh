#!/bin/bash
set -e

echo "Configuring primary database for replication..."

# Append replication rules to pg_hba.conf
echo "host replication all all trust" >> "$PGDATA/pg_hba.conf"

# Ensure replication settings are in postgresql.conf
echo "wal_level = replica" >> "$PGDATA/postgresql.conf"
echo "max_wal_senders = 10" >> "$PGDATA/postgresql.conf"
echo "max_replication_slots = 10" >> "$PGDATA/postgresql.conf"
echo "hot_standby = on" >> "$PGDATA/postgresql.conf"

echo "Primary replication configuration complete."
