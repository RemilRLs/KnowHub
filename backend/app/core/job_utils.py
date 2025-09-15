from dramatiq.message import Message
from app.tasks.ingest import ingest_document

def build_message_for(job_id: str, queue_name: str) -> Message:
    return Message(
        queue_name=queue_name,
        actor_name=ingest_document.actor_name,
        args=(),
        kwargs={},
        options={},
        message_id=job_id,
    )
