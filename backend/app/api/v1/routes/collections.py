import logging
from fastapi import APIRouter, HTTPException
from app.config.config import PGVECTOR_DSN
from app.core.pgvector.pgvector import PgVectorStore

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/", response_model=list[str])
def list_collections():
    """
    Lists all available vector collections (tables).
    """
    try:
        pgvector_store = PgVectorStore(dsn=PGVECTOR_DSN)
        tables = pgvector_store.list_tables()
        pgvector_store.pg_pool.disconnect()
        return tables
    except Exception as e:
        logger.error(f"Error listing collections: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list collections: {str(e)}"
        )
