# app/tasks/actors.py
import dramatiq
from . import results_backend  

@dramatiq.actor(store_results=True, max_retries=3)
def ingest_document(doc_id: str):
    return {"ok": True, "doc_id": doc_id}
