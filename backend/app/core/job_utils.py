from typing import Any, Optional, Union
from dramatiq.message import Message

ActorLike = Union[str, Any]

def _resolve_actor_name(actor: ActorLike) -> str:
    if isinstance(actor, str):
        return actor
    name = getattr(actor, "actor_name", None)
    if isinstance(name, str) and name:
        return name
    raise ValueError(
        "actor must be a str (actor name) or a Dramatiq actor (with .actor_name)."
    )

def build_message_for(job_id: str, queue_name: str, actor: Optional[ActorLike]) -> Message: #t

    if not actor:
        raise ValueError("actor is required to fetch results (need actor_name).")
    actor_name = _resolve_actor_name(actor)
    return Message(
        queue_name=queue_name,
        actor_name=actor_name,
        args=(),
        kwargs={},
        options={},
        message_id=job_id,
    )
