import dramatiq
from . import broker

@dramatiq.actor(max_retries=3)
def ingest_document(document_id: str):
    print(f"Processing document with ID: {document_id}")
    return "test"