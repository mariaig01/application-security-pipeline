#!/bin/sh
set -eu

# psql variables quote the password as a SQL literal, not executable SQL.
psql --set=ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  --set=app_password="$DB_APP_PASSWORD" <<'SQL'
CREATE ROLE appsec LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD :'app_password';
GRANT USAGE, CREATE ON SCHEMA public TO appsec;
SQL
