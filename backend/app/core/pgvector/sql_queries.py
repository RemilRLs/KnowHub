TABLE_EXISTS_QUERY = """
    SELECT EXISTS (
        SELECT 1
        FROM information_schema.tables
        WHERE table_schema = %s AND table_name = %s
    );
"""

ENSURE_EXTENSION_QUERY = "CREATE EXTENSION IF NOT EXISTS vector;"

CREATE_TABLE_QUERY = """
    CREATE TABLE IF NOT EXISTS {tbl} (
    id BIGSERIAL PRIMARY KEY,
    embedding VECTOR({dim}) NOT NULL,
    text TEXT NOT NULL,
    source VARCHAR(512) NOT NULL,
    page INT NOT NULL,
    creation_date TIMESTAMPTZ NOT NULL DEFAULT now(),
    skillsets VARCHAR(256)[],
    title VARCHAR(512),
    author VARCHAR(256),
    url TEXT,
    ts_vector_en TSVECTOR GENERATED ALWAYS AS (
        to_tsvector('english', coalesce(text, ''))
    ) STORED,
    ts_vector_fr TSVECTOR GENERATED ALWAYS AS (
        to_tsvector('french', coalesce(text, ''))
    ) STORED
    );
"""

CREATE_HNSW_INDEX_QUERY = """
    CREATE INDEX IF NOT EXISTS {idx} ON {tbl}
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = {m}, ef_construction = {ef});
"""

CREATE_IVFFLAT_INDEX_QUERY = """
    CREATE INDEX IF NOT EXISTS {idx} ON {tbl}
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = {lists})
"""

DROP_TABLE_QUERY = "DROP TABLE IF EXISTS {tbl};"

LIST_TABLES_QUERY = """
    SELECT table_name
    FROM information_schema.tables
    WHERE table_schema = %s;
"""

DELETE_ROWS_BY_SOURCE_QUERY = "DELETE FROM {tbl} WHERE source = %s;"

CHECK_EXISTING_SOURCES_QUERY = """
    SELECT DISTINCT source
    FROM {tbl}
    WHERE source = ANY(%s)
"""

INSERT_CHUNK_QUERY = """
    INSERT INTO {tbl} (embedding, text, source, page, title, author, url)
    VALUES (%s, %s, %s, %s, %s, %s, %s)
"""

READ_EMBEDDINGS_SELECT_COLS = (
    "id, text, source, page, skillsets, title, author, url, "
    "creation_date, embedding <-> %s AS distance"
)

READ_EMBEDDINGS_WITH_WHERE_QUERY = """
    SELECT {cols}
    FROM {table}
    WHERE {where}
    ORDER BY embedding <-> %s
    LIMIT %s
"""

READ_EMBEDDINGS_QUERY = """
    SELECT {cols}
    FROM {table}
    ORDER BY embedding <-> %s
    LIMIT %s
"""

WHERE_SOURCE_QUERY = "source = ANY(%s)"
WHERE_THRESHOLD_QUERY = "embedding <-> %s <= %s"

SET_HNSW_EF_SEARCH_QUERY = "SET hnsw.ef_search = {}"

READ_FTS_QUERY = """
    WITH q AS (
    SELECT
        websearch_to_tsquery('english', %(q)s) AS q_en,
        websearch_to_tsquery('french',  %(q)s) AS q_fr
    )
    SELECT
    id, text, source, page, creation_date, title, author, url,
    GREATEST(
        COALESCE(ts_rank_cd(ts_vector_en, q.q_en), 0),
        COALESCE(ts_rank_cd(ts_vector_fr, q.q_fr), 0)
    ) AS fts_rank
    FROM {table}, q
    WHERE (ts_vector_en @@ q.q_en) OR (ts_vector_fr @@ q.q_fr)
    ORDER BY fts_rank DESC NULLS LAST
    LIMIT %(k)s;
"""
