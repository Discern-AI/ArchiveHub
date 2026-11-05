# PostgreSQL 16 with PostGIS (spatial) and pgvector (AI search). ADR-004.
FROM postgis/postgis:16-3.5

RUN apt-get update \
    && apt-get install -y --no-install-recommends postgresql-16-pgvector \
    && rm -rf /var/lib/apt/lists/*

COPY init.sql /docker-entrypoint-initdb.d/20-archivehub.sql
