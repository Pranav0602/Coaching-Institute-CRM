-- ---------------------------------------------------------------------------
-- Runs once, on first initialisation of the postgres data volume.
--
-- pgvector must exist server-side before any RAG migration can create a vector
-- column. Creating it here means a fresh `docker compose up` is immediately ready
-- and `manage.py check` reports crm.E002 / crm.W004 cleanly.
--
-- For a local (non-Docker) PostgreSQL, run the same statement manually:
--   psql -U postgres -d Institute_CRM -c "CREATE EXTENSION IF NOT EXISTS vector;"
-- ---------------------------------------------------------------------------

CREATE EXTENSION IF NOT EXISTS vector;

-- Trigram index support for fuzzy name/lead search in the CRM.
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Case-insensitive text, used for email uniqueness comparisons.
CREATE EXTENSION IF NOT EXISTS citext;
