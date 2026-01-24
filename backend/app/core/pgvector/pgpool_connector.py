import psycopg_pool
from psycopg import sql
from typing import Optional
from contextlib import contextmanager
from pgvector.psycopg import register_vector

class PgPoolConnector:
    """
    PostgreSQL connector with connection pooling using psycopg3.
    Recommended for production environments with multiple concurrent requests.
    """

    def __init__(
        self,
        dsn: str,
        min_size: int = 2,
        max_size: int = 10,
        enable_vector: bool = True
    ):
        """
        Initialize the PostgreSQL connection pool.
        
        Args:
            dsn: Database connection string
            min_size: Minimum number of connections in the pool
            max_size: Maximum number of connections in the pool
            enable_vector: Enable pgvector extension support
        """
        self.dsn = dsn
        self.enable_vector = enable_vector
        self._pool: Optional[psycopg_pool.ConnectionPool] = None
        self.min_size = min_size
        self.max_size = max_size

    def connect(self):
        """
        Initialize the connection pool.
        """

        if self._pool is None:
            self._pool = psycopg_pool.ConnectionPool(
                self.dsn,
                min_size=self.min_size,
                max_size=self.max_size,
                configure=self._configure_connection, # For autocommit and vectors.
                check=psycopg_pool.ConnectionPool.check_connection # Check with a SELECT 1 or something else I don't know.
            )

    def _configure_connection(self, conn):
        conn.autocommit = True # To commit after executing each SQL command.
        if self.enable_vector:
            register_vector(conn)

    def disconnect(self):
        """
        Close the connection pool
        """
        if self._pool:
            self._pool.close()
            self._pool = None

    @contextmanager
    def cursor(self):
        """
        Context manager for getting a cursor from the pool.
        
        Yields:
            psycopg.Cursor: Database cursor
        """
        if self._pool is None:
            self.connect()
            
        with self._pool.connection() as conn: # Already have a connection when initialize the class with connect method.
            with conn.cursor() as cur: # At the end of the with, both cursor and connection are returned to the pool because thanks to the context managers.
                # No need to close manually with a finally (the context manager does it).
                # __enter__ and __exit__ methods of the connection and cursor handle that.
                yield cur

    def is_connected(self) -> bool:
        return self._pool is not None