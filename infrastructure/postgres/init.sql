-- Enable extensions required by SmartDesk AI.
-- pgvector: semantic search / embeddings (Phase 6+)
-- pg_trgm: fuzzy text search for ticket/KB search
-- uuid-ossp: UUID generation helpers (defense-in-depth; app uses uuid4 too)
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";