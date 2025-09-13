from fastapi import APIRouter
from app.tasks.ingest import ingest_document

router = APIRouter()

@router.post("/")
def enqueue_ingest(doc_id: str):
    msg = ingest_document.send(doc_id)
    print(f"Message is : {msg}")
    return {"message": f"Document {doc_id} enqueued for ingestion."}