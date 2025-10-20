import psycopg
import os

from psycopg import sql
from dotenv import load_dotenv
from pgvector.psycopg import Vector, register_vector
from typing import Any, Dict, List, Optional

from langchain_core.documents import Document


from app.core.pgvector_utils import PgVectorUtils

class PgVectorStore:
    """
    
    """

    def __init__(self, dsn: str, schema: str = "public"):
        self.dsn = dsn
        self.schema = schema
        self.pg_utils = PgVectorUtils()
    
        self.connection_db()


    def connection_db(self):
        """
        
        """
        self.connector = psycopg.connect(self.dsn, autocommit=True)
        register_vector(self.connector)  # Register the Vector type with the connection.

    def close_connection(self):
        """
        
        """
        if self.connector:
            self.connector.close()

    def check_if_connected(self) -> bool:
        """
        
        """
        pass 


  
    def table_exists(self, table_name: str) -> bool:
        """
        Checks if a table with the specified name exists in the given schema.
        Args:
            table_name (str): The name of the table to check for existence.
        Returns:
            bool: True if the table exists, False otherwise.
        """
        with self.connector.cursor() as cur:
            cur.execute("""
                SELECT EXISTS (
                    SELECT 1
                    FROM information_schema.tables
                    WHERE table_schema = %s AND table_name = %s
                );
            """, (self.schema, table_name))
            
            return bool(cur.fetchone()[0])
        
    def ensure_extension(self):
        """
        Ensures that the 'vector' extension is installed in the PostgreSQL database.

        Connects to the database using the provided DSN and executes a SQL command to
        create the 'vector' extension if it does not already exist. This extension is
        required for vector operations in PostgreSQL.

        Raises:
            psycopg.Error: If there is an error connecting to the database or executing the SQL command.
        """
        with self.connector.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    def ensure_index_type(self, index_type: str) -> bool:
        valid_index_types = ["hnsw", "ivfflat"]
        if index_type.lower() not in valid_index_types:
            return False
        return True

    def create_vector_collection(self,
                                 collection_name: str,
                                 dim: int,
                                 index_type: str = "hnsw",  # Hierarchical Navigable Small World Graph.
                                 hnsw_m: int = 32,  # Maximum connections per node in the graph (higher value increases accuracy).
                                 hnsw_ef_construction: int = 400,  # Number of candidates considered during construction (improves node selection).
                                 ivf_lists: int = 1000, # Number of clusters.
                                 ) -> bool:
        """
        Creates a new vector collection (table) in the database with the specified dimension and index type.

        Args:
            collection_name (str): Name of the collection (table) to create.
            dim (int): Dimension of the vector embeddings.
            index_type (str, optional): Type of index to use ("hnsw" or "ivfflat"). Defaults to "hnsw".
            hnsw_m (int, optional): Maximum connections per node in HNSW graph. Defaults to 32.
            hnsw_ef_construction (int, optional): Number of candidates considered during HNSW construction. Defaults to 400.
            ivf_lists (int, optional): Number of clusters for IVFFlat index. Defaults to 1000.

        Returns:
            bool: True if the collection was created successfully, False if it already exists.
        """
        
        # Ensure the pgvector extension is enabled.
        self.ensure_extension()

        # Ensure index type.

        if not self.ensure_index_type(index_type):
            return False

        # Check if the collection (table) already exists.
        if self.table_exists(collection_name):
            print(f"Table {collection_name} already exists.")
            return False

        collection_name = collection_name.lower()

        tbl = sql.Identifier(collection_name)  # Prevent SQL injection.
        idx = sql.Identifier(f"{collection_name}_vec_idx")

        with self.connector.cursor() as cur:
            cur.execute(
                sql.SQL("""
                    CREATE TABLE IF NOT EXISTS {} (
                    id BIGSERIAL PRIMARY KEY,
                    embedding VECTOR(1024) NOT NULL,
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
                """).format(
                    sql.Identifier(collection_name)
                )
            )

            # No index have been choosed (either HNSW or IVFFLAT).
            if index_type is None:
                return True

            # Creation of the index HNSW
            if index_type.lower() == "hnsw":
                cur.execute(
                    sql.SQL("""
                        CREATE INDEX IF NOT EXISTS {} ON {}
                        USING hnsw (embedding vector_cosine_ops)
                        WITH (m = {}, ef_construction = {});
                    """).format(
                        idx,
                        tbl,
                        sql.Literal(hnsw_m),
                        sql.Literal(hnsw_ef_construction),
                    )
                )
            elif index_type.lower() == "ivfflat": # IVFFlat : Inverted File with Flat Compression
                cur.execute(
                    sql.SQL("""
                        CREATE INDEX IF NOT EXISTS {} ON {}
                        USING ivfflat (embedding vector_cosine_ops)
                        WITH (lists = {})
                    """).format(
                        idx,
                        tbl,
                        sql.Literal(ivf_lists)
                    )
                )
            else:
                raise ValueError("index_type must be 'hnsw', 'ivfflat', or None")
            return True

    def drop_table(self, table_name: str) -> bool:
        """
        
        """

        if not self.table_exists(table_name):
            print(f"Cannot delete a table {table_name} that doesn't exist.")
            return False

        table_name = table_name.lower()
        tbl = sql.Identifier(table_name)

        with self.connector.cursor() as cur:
            cur.execute(
                sql.SQL("""
                    DROP TABLE IF EXISTS {};
                """).format(
                    tbl
                )
            )
            return True
        
    def list_tables(self) -> List[str]:
        """
        
        """
        with self.connector.cursor() as cur:
            cur.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = %s;
            """, (self.schema,))
            tables = [row[0] for row in cur.fetchall()]
        return tables
    
    def delete_rows_by_source(self, table_name: str, source: str) -> int:
        """
        Deletes rows from the specified table where the 'source' column matches the given source identifier.
        Args:
            table_name (str): The name of the table from which rows will be deleted. 
                              The table name is case-insensitive and will be converted to lowercase.
            source (str): The source identifier (e.g., filename) to match for deletion. 
                          Must be a non-empty string.
        Returns:
            int: The number of rows deleted from the table.
        Raises:
            ValueError: If the `source` is None or an empty string.
            ValueError: If the specified `table_name` does not exist.
        Notes:
            - This method assumes the existence of a 'source' column in the specified table.
            - The `table_exists` method is used to verify the existence of the table before attempting deletion.
            - The operation is performed using a PostgreSQL database connection.
        """

        if source is None or source.strip() == "":
            raise ValueError("Source must be a non-empty string.")
        if not self.table_exists(table_name):
            raise ValueError(f"Table {table_name} does not exist.")
        
        table_name = table_name.lower()
        tbl = sql.Identifier(table_name)

        with self.connector.cursor() as cur:
            cur.execute(
                sql.SQL("""
                    DELETE FROM {} WHERE source = %s;
                """).format(
                    tbl
                ),
                (source,)
            )
            deleted_count = cur.rowcount
        return deleted_count

    def delete_rows_by_skillsets(self):
        pass

    def insert_chunks(
            self,
            docs: List[Document],
            collection: str,
    ):
        """
        Inserts chunks into the collection after first checking if the sources already exist.
        Chunks are grouped by source to optimize checks.
        """
        if not docs:
            print("No documents to insert")
            return

        print(f"Preparing {len(docs)} chunks for insertion into the collection '{collection}'")

        # Verify that the collection exists
        if not self.table_exists(collection):
            print(f"Collection '{collection}' does not exist, creating it...")
            if not self.create_vector_collection(collection, dim=1024, index_type="hnsw"):
                raise RuntimeError(f"Unable to create the collection '{collection}'")

        # Prepare the data
        texts, metadatas, embeddings = self.pg_utils.prepare_chunks(docs)
        
        if not texts:
            print("No valid text found after preparation")
            return

        # Group by source
        sources_groups = {}
        for i, (text, metadata, embedding) in enumerate(zip(texts, metadatas, embeddings)):
            source = metadata.get('file_name', 'unknown')
            if source not in sources_groups:
                sources_groups[source] = []
            sources_groups[source].append({
                'text': text,
                'metadata': metadata,
                'embedding': embedding
            })

        print(f"Grouped into {len(sources_groups)} sources: {list(sources_groups.keys())}")

        # Check for existing sources
        existing_sources = self._check_existing_sources(collection, list(sources_groups.keys()))
        
        # Insert only new sources
        total_inserted = 0
        for source, chunks in sources_groups.items():
            if source in existing_sources:
                print(f"Source '{source}' already exists, skipping {len(chunks)} chunks")
                continue
                
            print(f"Inserting {len(chunks)} chunks for source '{source}'")
            inserted_count = self._insert_chunks_for_source(collection, source, chunks)
            total_inserted += inserted_count

        print(f"Insertion complete: {total_inserted} chunks inserted in total")

    def _check_existing_sources(self, collection: str, sources: List[str]) -> set:
        """
        Checks which sources already exist in the collection.
        
        Args:
            collection: Name of the collection (table)
            sources: List of sources to check
            
        Returns:
            Set of sources that already exist
        """
        if not sources:
            return set()
            
        collection = collection.lower()
        table_identifier = sql.Identifier(collection)
        
        # Use ANY to check multiple sources in a single query
        with self.connector.cursor() as cur:
            cur.execute(
                sql.SQL("""
                    SELECT DISTINCT source 
                    FROM {} 
                    WHERE source = ANY(%s)
                """).format(table_identifier),
                (sources,)
            )
            existing = {row[0] for row in cur.fetchall()}
            
        if existing:
            print(f"Existing sources found: {existing}")
        
        return existing

    def _insert_chunks_for_source(self, collection: str, source: str, chunks: List[Dict]) -> int:
        """
        Inserts all chunks for a given source into the collection.
        
        Args:
            collection: Name of the collection (table)
            source: Name of the source file
            chunks: List of chunks with text, metadata, embedding from the source file
            
        Returns:
            Number of chunks inserted
        """
        collection = collection.lower()
        table_identifier = sql.Identifier(collection)
        
        insert_query = sql.SQL("""
            INSERT INTO {} (embedding, text, source, page, title, author, url)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """).format(table_identifier)
        
        inserted_count = 0
        with self.connector.cursor() as cur:
            for chunk in chunks:
                try:
                    metadata = chunk['metadata']
                    embedding_vector = Vector(chunk['embedding'])
                    text = chunk['text']

                    cur.execute(insert_query, (
                        embedding_vector,
                        text,
                        source,
                        metadata.get('page', 0),
                        metadata.get('title'),
                        metadata.get('author'),
                        metadata.get('url')
                    ))
                    inserted_count += 1
                except Exception as e:
                    print(f"Error while inserting a chunk for '{source}': {e}")
                    continue
            return inserted_count

    def read_embeddings(self, 
                        table: str, # Name of the collection (table).
                        prompt: str, # Prompt to be embedded.
                        k: int = 16, # Number of nearest chunks to return
                        ef_search: Optional[int] = 150, # HNSW : Number of candidates considered during search (improves accuracy)
                        sources: Optional[List[str]] = None,
                        threshold: Optional[float] = None # Maximum distance threshold (filters out results with distance > threshold)
                        ):
        """
        Retrieves the k nearest embeddings to the given prompt from the specified table.
        
        Args:
            table (str): Name of the collection (table).
            prompt (str): Prompt to be embedded.
            embed_func: Embedding function to use.
            k (int): Number of nearest chunks to return.
            ef_search (Optional[int]): HNSW ef_search parameter.
            sources (Optional[List[str]]): Optional list of sources to filter by.
            threshold (Optional[float]): Maximum distance threshold. Results with distance > threshold are excluded.
        
        Returns:
            List[Dict[str, Any]]: List of dictionaries containing the retrieved rows with their distances.
        """

        table_identifier = sql.Identifier(table.lower())

        qvec = Vector(self.pg_utils.embed([prompt])[0])
        select_sql = sql.SQL("id, text, source, page, skillsets, title, author, url, creation_date, embedding <-> %s AS distance")

        # Build query with optional WHERE clause for sources and threshold
        where_clauses = []
        if sources is not None and len(sources) > 0:
            where_clauses.append(sql.SQL("source = ANY(%s)"))
        if threshold is not None:
            where_clauses.append(sql.SQL("embedding <-> %s <= %s")) # First %s is query vector, second is threshold
        
        if where_clauses:
            where_sql = sql.SQL(" AND ").join(where_clauses)
            query = sql.SQL("""
                SELECT {cols}
                FROM {table}
                WHERE {where}
                ORDER BY embedding <-> %s 
                LIMIT %s
            """).format(cols=select_sql, table=table_identifier, where=where_sql)
            
            query_params = [qvec] # User query and other parameters
            if sources is not None and len(sources) > 0:
                query_params.append(sources)
            if threshold is not None:
                query_params.extend([qvec, threshold])
            query_params.extend([qvec, k])
            query_params = tuple(query_params)
        else: # Nearest neighbor search without filtering (no WHERE clause)
            query = sql.SQL("""
                SELECT {cols}
                FROM {table}
                ORDER BY embedding <-> %s 
                LIMIT %s
            """).format(cols=select_sql, table=table_identifier)
            query_params = (qvec, qvec, k)

        results: List[Dict[str, Any]] = []

        with self.connector.cursor() as cur:
            if ef_search is not None:
                cur.execute(sql.SQL("SET hnsw.ef_search = {}").format(sql.Literal(int(ef_search))))
            
            cur.execute(query, query_params)
            rows = cur.fetchall()
            colnames = [desc.name for desc in cur.description]
            for row in rows:
                rec = dict(zip(colnames, row))
                if rec.get("distance") is not None:
                    rec["distance"] = float(rec["distance"])
                results.append(rec)
        
        return results 
    
    def read_hybrid(self,
                    table: str,
                    prompt: str,
                    embed_func,
                    k: int = 16,
                    ef_search: Optional[int] = 150,
                    rrf_k: int = 60,
                    top_k: Optional[int] = None
                    ) -> List[Dict[str, Any]]:
        """
        Performs hybrid search combining vector similarity and full-text search using 
        Reciprocal Rank Fusion (RRF).
        
        Args:
            table (str): Name of the collection (table).
            prompt (str): Search query text.
            embed_func: Function to embed the prompt into a vector.
            k (int): Number of results to retrieve from each method.
            ef_search (Optional[int]): HNSW ef_search parameter.
            rrf_k (int): RRF constant (typically 60). Higher values give more weight to lower ranks.
            top_k (Optional[int]): Number of final results to return after RRF. If None, returns k results.
            
        Returns:
            List[Dict[str, Any]]: List of deduplicated and re-ranked results with RRF scores.
        """
        # Get results from both methods
        vector_results = self.read_embeddings(table, prompt, embed_func, k, ef_search) 
        fts_results = self.read_fts(table, prompt, k)
        
        # RRF scoring: score = sum(1 / (rank + k)) for each retrieval method
        rrf_scores: Dict[int, float] = {}
        doc_data: Dict[int, Dict[str, Any]] = {}
        
        # Process vector search results
        for rank, doc in enumerate(vector_results, start=1):
            doc_id = doc["id"] # ID is the primary key of the table
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + (1.0 / (rrf_k + rank)) # Either initialize or add to the score (can sum up)
            if doc_id not in doc_data:
                doc_data[doc_id] = doc.copy() # All fields of the document
                doc_data[doc_id]["vector_rank"] = rank # Is rank of the document in vector search
                doc_data[doc_id]["fts_rank"] = None
        
        # Process FTS results
        for rank, doc in enumerate(fts_results, start=1):
            doc_id = doc["id"] # ID is the primary key of the table
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + (1.0 / (rrf_k + rank))
            if doc_id not in doc_data:
                doc_data[doc_id] = doc.copy()
                doc_data[doc_id]["vector_rank"] = None
                doc_data[doc_id]["fts_rank"] = rank
            else:
                doc_data[doc_id]["fts_rank"] = rank
        
        # Sort by RRF score and add to results
        sorted_doc_ids = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)
        
        # Use top_k if specified, otherwise use k
        final_k = top_k if top_k is not None else k
        
        results = []
        for doc_id in sorted_doc_ids[:final_k]:
            doc = doc_data[doc_id]
            doc["rrf_score"] = rrf_scores[doc_id]
            results.append(doc)
        
        return results

    def read_fts(self, 
                 table: str, # Name of the collection (table).
                 prompt: str, # Prompt to be embedded.
                 k: int = 16 # Number of nearest chunks to return
                ) -> List[Dict[str, Any]]:
        """
        Implementation of Full-Text Search with improved ranking.
        Uses ts_rank with normalization and considers both exact matches and proximity.
        """
        
        query = sql.SQL("""
            WITH q AS (
                SELECT
                    websearch_to_tsquery('english', %(q)s) AS q_en,
                    websearch_to_tsquery('french',  %(q)s) AS q_fr,
                    plainto_tsquery('english', %(q)s) AS q_plain_en,
                    plainto_tsquery('french',  %(q)s) AS q_plain_fr
            )
            SELECT
                id, text, source, page, creation_date, title, author, url,
                GREATEST(
                    -- Use ts_rank with document length normalization (flag 1)
                    -- Higher weight for exact phrase matches
                    COALESCE(
                        ts_rank(ts_vector_en, q.q_en, 1) * 2.0 +
                        ts_rank(ts_vector_en, q.q_plain_en, 1),
                        0
                    ),
                    COALESCE(
                        ts_rank(ts_vector_fr, q.q_fr, 1) * 2.0 +
                        ts_rank(ts_vector_fr, q.q_plain_fr, 1),
                        0
                    )
                ) AS fts_rank
            FROM {table}, q
            WHERE (ts_vector_en @@ q.q_en OR ts_vector_en @@ q.q_plain_en) 
               OR (ts_vector_fr @@ q.q_fr OR ts_vector_fr @@ q.q_plain_fr)
            ORDER BY fts_rank DESC NULLS LAST
            LIMIT %(k)s;
        """).format(table=sql.Identifier(table.lower()))

        results: List[Dict[str, Any]] = []

        with self.connector.cursor() as cur:
            cur.execute(query, {"q": prompt, "k": k})
            rows = cur.fetchall()
            colnames = [desc.name for desc in cur.description]
            for row in rows:
                rec = dict(zip(colnames, row))
                if rec.get("fts_rank") is not None:
                    rec["fts_rank"] = float(rec["fts_rank"])
                results.append(rec)

        return results

if __name__ == "__main__":
    load_dotenv()
    print("\n--- Initializing PgVectorStore ---")
    dsn = f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@localhost:5433/{os.getenv('POSTGRES_DB')}"
    pgvector_store = PgVectorStore(dsn)

    # pgvector_store.drop_table("my_collection")
    print("\n--- Testing create_vector_collection ---")

    if(pgvector_store.create_vector_collection("my_collection", dim=1024, index_type="hnsw")):
        print("Collection created successfully.")
    else:
        print("Collection already exists or an error occurred.")

    # Test read_embeddings
    print("\n--- Testing read_embeddings ---")
    prompt = "La Global Business Unit Cybersecurity & Digital Identity (CDI) de Thales regroupe plusieurs activités..."

    print(f"Query prompt: '{prompt}'")
    
    results = pgvector_store.read_embeddings(
        table="string",
        prompt=prompt,
        k=5,
        ef_search=150
    )
    
    print(f"\nFound {len(results)} results:")
    for i, result in enumerate(results, 1):
        print(f"\nResult {i}:")
        print(f"  ID: {result.get('id')}")
        print(f"  Text: {result.get('text', '')[:100]}...")  # First 100 chars
        print(f"  Source: {result.get('source')}")
        print(f"  Page: {result.get('page')}")
        print(f"  Distance: {result.get('distance'):.4f}")

    # Test read_fts
    print("\n--- Testing read_fts ---")
    fts_prompt = "Global Business Unit"
    print(f"FTS query: '{fts_prompt}'")
    
    fts_results = pgvector_store.read_fts(
        table="string",
        prompt=fts_prompt,
        k=5
    )
    
    print(f"\nFound {len(fts_results)} FTS results:")
    for i, result in enumerate(fts_results, 1):
        print(f"\nResult {i}:")
        print(f"  ID: {result.get('id')}")
        print(f"  Text: {result.get('text', '')}")
        print(f"  Source: {result.get('source')}")
        print(f"  Page: {result.get('page')}")
        print(f"  FTS Rank: {result.get('fts_rank'):.4f}")

    # Closing
    pgvector_store.close_connection()