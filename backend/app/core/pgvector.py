import psycopg
import os

from psycopg import sql
from dotenv import load_dotenv
from pgvector.psycopg import Vector
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
        insert_chunks_grouped_by_source_skip_existing
        """

        texts, metadata = self.pg_utils.prepare_chunks(docs)

        print(f"Inserting {len(texts)} chunks into collection '{collection}'")

        for text in texts:
            print(f"Text chunk: {text[:30]}...")

        for meta in metadata:
            print(f"Metadata: {meta}")

    def read_embeddings(self, 
                        table: str, # Name of the collection (table).
                        prompt: str, # Prompt to be embedded.
                        embed_func, # To be replaced by the embedder function (vLLM CortAIx) - Name of the function to use : embed_query(self, text:str) -> List[float]
                        k: int = 16, # Number of nearest chunks to return
                        ef_search: Optional[int] = 150 # HNSW : Number of candidates considered during search (improves accuracy)
                        ):
        """
        
        """

        table_identifier = sql.Identifier(table.lower())

        qvec = Vector(embed_func(prompt))
        select_sql = sql.SQL("id, text, source, page, skillsets, title, author, url, creation_date, embedding <-> %s AS distance")


        # ORDY BY embedding <-> %s : To get the nearest neighbors based on cosine distance (most similar vectors first).
        query = sql.SQL("""
            SELECT {cols}
            FROM {table}
            ORDER BY embedding <-> %s 
            LIMIT %s
        """).format(cols=select_sql, table=table_identifier)

        results: List[Dict[str, Any]] = []

        with self.connector.cursor() as cur:
            if ef_search is not None:
                cur.execute(sql.SQL("SET hnsw.ef_search = {}").format(sql.Literal(int(ef_search))))
            
            cur.execute(query, (qvec, qvec, k))
            rows = cur.fetchall() # Get all results.
            colnames = [desc.name for desc in cur.description] # I get all column names such as ['id', 'text', 'source', 'page', 'distance', ...]
            for row in rows:
                rec = dict(zip(colnames, row)) # Create a dictionary for each row.
                if rec.get("distance") is not None:
                    rec["distance"] = float(rec["distance"]) # Convert distance to float.
                results.append(rec)

    def read_fts(self):
        pass

if __name__ == "__main__":
    load_dotenv()
    dsn = f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@localhost:5433/{os.getenv('POSTGRES_DB')}"
    pgvector_store = PgVectorStore(dsn)

    # pgvector_store.drop_table("my_collection")

    if(pgvector_store.create_vector_collection("my_collection", dim=1024, index_type="hnsw")):
        print("Collection created successfully.")
    else:
        print("Collection already exists or an error occurred.")

    # Closing

    pgvector_store.close_connection()