import logging
import dramatiq
import json
import time 
import os

from typing import Dict, Any, List, Optional
from datetime import datetime

from dramatiq.results import Results
from dramatiq.results.backends import RedisBackend

from app.core.pgvector.pgvector import PgVectorStore
from app.config.config import PGVECTOR_DSN
from app.config.paths import SESSIONS_DIR
from app.core.redis_config import redis_client

STREAM_PREFIX = "knowhub:stream"
STREAM_TTL_SECONDS = 3600

from app.core.generator.llmprovider import LLMFactory
from app.core.promptbuilder import PromptBuilder, PromptType
from app.config.llm_settings import llm_settings

logger = logging.getLogger(__name__)

results_backend = RedisBackend(client=redis_client)

def _build_context(chunks: List[Dict[str, Any]]) -> str:
    """
    Builds context from retrieved chunks.
    """
    context_parts = []
    
    for i, chunk in enumerate(chunks, 1):
        text = chunk.get('text', '')
        source = chunk.get('source', 'Unknown')
        page = chunk.get('page', 'N/A')
        distance = chunk.get('distance', 0.0)
        
        context_parts.append(
            f"[Chunk number {i} - {source} (page {page}) - distance: {distance:.3f}]\n{text}\n"
        )
    
    return "\n---\n".join(context_parts)

def _get_chunk_numbers(retrieved_chunks: List[Dict[str, Any]]) -> Dict[str, List[int]]:
    """
    Map chunk text to its chunk numbers.
    """

    chunk_map = {}
    for idx, chunk in enumerate(retrieved_chunks, 1):
        text = chunk.get('text', '')
        if text not in chunk_map:
            chunk_map[text] = []
        chunk_map[text].append(idx)

    return chunk_map

def _get_unique_source(retrieved_chunks: List[Dict[str, Any]]) -> List[str]:
    """
    Extract unique sources from retrieved chunks.
    """
    sources = set()
    for chunk in retrieved_chunks:
        source = chunk.get('source', 'Unknown')
        sources.add(source)
    return list(sources)

def _generate_with_llm(
        query: str,
        context: str,
        max_tokens: int = 2048,
        temperature: float = 0.5
) -> str:
    """
    Generating answer using context with LLM.
    """

    messages = _build_messages(query=query, context=context)

    try:
        # Creation of the correct class link to the provider.

        llm = LLMFactory.create(
            provider=llm_settings.LLM_PROVIDER,
            model=llm_settings.LLM_MODEL,
            temperature=temperature,
            api_key=llm_settings.OPENAI_API_KEY if llm_settings.LLM_PROVIDER == "openai" else llm_settings.ANTHROPIC_API_KEY,
        )

        logger.info(f"messages for LLM: {messages}")

        # Now we have an instance of the choosen provider (by the user).
        answer = llm.generate_chat(messages=messages)
        
        return answer
    
    except Exception as e:
        logger.error(f"LLM generation error: {str(e)}", exc_info=True)
        return f"Erreur lors de la génération de la réponse: {str(e)}"


def _build_messages(query: str, context: str):
    prompt_builder = PromptBuilder(PromptType.RAG_GENERATION)
    return prompt_builder.add_variables(
        query=query,
        context=context
    ).build_messages()


def _stream_with_llm(
    query: str,
    context: str,
    max_tokens: int = 2048,
    temperature: float = 0.5,
):
    messages = _build_messages(query=query, context=context)

    try:
        llm = LLMFactory.create(
            provider=llm_settings.LLM_PROVIDER,
            model=llm_settings.LLM_MODEL,
            temperature=temperature,
            api_key=llm_settings.OPENAI_API_KEY if llm_settings.LLM_PROVIDER == "openai" else llm_settings.ANTHROPIC_API_KEY,
        )

        logger.info(f"messages for LLM: {messages}")

        try:
            for token in llm.stream_chat(messages=messages, max_tokens=max_tokens):
                yield token
        except NotImplementedError:
            answer = llm.generate_chat(messages=messages, max_tokens=max_tokens)
            yield answer

    except Exception as e:
        logger.error(f"LLM streaming error: {str(e)}", exc_info=True)
        raise

def _stream_publish(stream_key: str, event_type: str, data: Any):
    payload = json.dumps(data, ensure_ascii=False)
    redis_client.xadd(
        stream_key,
        {"type": event_type, "data": payload},
    )
    redis_client.expire(stream_key, STREAM_TTL_SECONDS)


def _save_session_to_json(
    job_id: str,
    query: str,
    answer: str,
    collection: str,
    sources: List[str],
    metadata: Dict[str, Any]
):
    """
    Save the session data to a JSON file.
    """

    try:
        os.makedirs(SESSIONS_DIR, exist_ok=True)

        session_data = {
            "job_id": job_id,
            "timestamp": datetime.utcnow().isoformat(),
            "query": query,
            "answer": answer,
            "collection": collection,
            "sources": sources,
            "metadata": metadata
        }  

        filepath = os.path.join(SESSIONS_DIR, f"{job_id}.json")
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(session_data, f, ensure_ascii=False, indent=4)
        
        logger.info(f"Session data saved to {filepath}")
    except Exception as e:
        logger.error(f"Error saving session data: {str(e)}", exc_info=True)

@dramatiq.actor(
    store_results=False,
    max_retries=3,
    queue_name="generation",
)
def generate_answer_stream(
    job_id: str,
    query: str,
    collection: str,
    k: int = 10,
    sources: Optional[List[str]] = None,
    max_tokens: int = 2048,
    temperature: float = 0.7,
):
    stream_key = f"{STREAM_PREFIX}:{job_id}"

    logger.info(
        "Starting RAG generation stream for job_id=%s query='%s...' collection='%s'",
        job_id,
        query[:50],
        collection,
    )

    start_time = time.time()
    store = PgVectorStore(dsn=PGVECTOR_DSN)

    full_answer = ""

    try:
        if not store.table_exists(collection):
            error_msg = f"Collection '{collection}' does not exist."
            logger.warning(error_msg)
            _stream_publish(stream_key, "error", {"error": error_msg})
            return

        retrieval_start = time.time()
        retrieved_chunks = store.read_embeddings(
            table=collection,
            prompt=query,
            k=k,
            sources=sources,
        )
        retrieval_time = (time.time() - retrieval_start) * 1000

        if not retrieved_chunks:
            no_info_msg = "I'm sorry, I couldn't find any relevant information to answer your question."
            full_answer = no_info_msg
            
            _stream_publish(
                stream_key,
                "token",
                no_info_msg,
            )
            _stream_publish(
                stream_key,
                "done",
                {
                    "sources": [],
                    "retrieved_chunks": 0,
                    "retrieval_time_ms": retrieval_time,
                    "generation_time_ms": 0,
                    "total_time_ms": (time.time() - start_time) * 1000,
                },
            )
            
            # We even save if no chunks were retrieved (audit)
            _save_session_to_json(
                job_id=job_id,
                query=query,
                answer=full_answer,
                collection=collection,
                sources=[],
                metadata={
                    "retrieved_chunks": 0,
                    "retrieval_time_ms": retrieval_time,
                    "generation_time_ms": 0,
                    "total_time_ms": (time.time() - start_time) * 1000,
                }
            )
            return

        context = _build_context(retrieved_chunks)

        generation_start = time.time()
        for token in _stream_with_llm(
            query=query,
            context=context,
            max_tokens=max_tokens,
            temperature=temperature,
        ):
            full_answer += token
            _stream_publish(stream_key, "token", token)

        generation_time = (time.time() - generation_start) * 1000
        total_time = (time.time() - start_time) * 1000
        unique_chunk_sources = _get_unique_source(retrieved_chunks)
        chunk_map = _get_chunk_numbers(retrieved_chunks)

        metadata = {
            "retrieved_chunks": len(retrieved_chunks),
            "retrieval_time_ms": retrieval_time,
            "generation_time_ms": generation_time,
            "total_time_ms": total_time,
            "chunk_map": chunk_map,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "k": k
        }

        _stream_publish(stream_key, "done", {**metadata, "sources": unique_chunk_sources})
        
        # Sauvegarder la session complète
        _save_session_to_json(
            job_id=job_id,
            query=query,
            answer=full_answer,
            collection=collection,
            sources=unique_chunk_sources,
            metadata=metadata
        )

    except Exception as e:
        logger.error(f"Error during streaming RAG generation: {str(e)}", exc_info=True)
        _stream_publish(stream_key, "error", {"error": str(e)})

    finally:
        store.pg_pool.disconnect()



@dramatiq.actor(
    store_results=True, 
    max_retries=3, 
    queue_name="generation"
)
def generate_answer(
    query: str,
    collection: str,
    k: int = 10,
    ef_search: Optional[int] = 150,
    sources: Optional[List[str]] = None,
    threshold: Optional[float] = None,
    max_tokens: int = 2048,
    temperature: float = 0.7,
) -> Dict[str, Any]:
    """
    RAG generation task: retrieval + generation.

    Args:
        query: User query
        collection: Collection to search
        k: Number of chunks to retrieve
        ef_search: HNSW search parameter
        sources: Filter by sources
        threshold: Similarity threshold
        max_tokens: Max tokens for generation
        temperature: Generation temperature
        
    Returns:
        Dictionary with answer, sources, and metadata
    """

    logger.info(f"Starting RAG generation for query: '{query[:50]}...' in collection '{collection}'")

    start_time = time.time() # For measuring total time and optimization for the future

    try:
        # Step 1: Retrieve relevant chunks from PGVector
        logger.info(f"Step 1/2: Retrieving {k} chunks from '{collection}'")
        retrieval_start = time.time()

        store = PgVectorStore(dsn=PGVECTOR_DSN)

        try:
            if not store.table_exists(collection):
                error_msg = f"Collection '{collection}' does not exist."
                return {
                    "status": "error",
                    "error": error_msg,
                    "query": query
                }
            
            # Retrieve relevant chunks
            retrieved_chunks = store.read_embeddings(
                table=collection,
                prompt=query,
                k=k,
                sources=sources,
            )
            
            retrieval_time = (time.time() - retrieval_start) * 1000
            logger.info(f"Retrieved {len(retrieved_chunks)} chunks in {retrieval_time:.2f}ms")
            logger.info(f"Sources retrieved: {[chunk for chunk in retrieved_chunks]}")

            chunk_map = _get_chunk_numbers(retrieved_chunks)
            logger.info(f"Chunk map: {chunk_map}")

            if not retrieved_chunks:
                logger.warning("No chunks retrieved, returning empty response")
                return {
                    "status": "success",
                    "query": query,
                    "answer": "Je n'ai pas trouvé d'informations pertinentes pour répondre à votre question.",
                    "sources": [],
                    "retrieved_chunks": 0,
                    "retrieval_time_ms": retrieval_time,
                    "generation_time_ms": 0,
                    "total_time_ms": (time.time() - start_time) * 1000
                }
            
            # Step2: Generate answer with context from retrieved chunks
            logger.info("Step 2/2: Generating answer with LLM")
            generation_start = time.time()

            # We build the context from the retrieved chunks
            context = _build_context(retrieved_chunks)

            answer = _generate_with_llm(
                query=query,
                context=context,
                temperature=temperature
            )

            generation_time = (time.time() - generation_start) * 1000
            total_time = (time.time() - start_time) * 1000

            logger.info(f"Answer : {answer}")
            unique_chunk_sources = _get_unique_source(retrieved_chunks)

            return {
                "status": "sucess",
                "query": query,
                "answer": answer,
                "sources": unique_chunk_sources,
                "retrieved_chunks": len(retrieved_chunks),
                "retrieval_time_ms": retrieval_time,
                "generation_time_ms": generation_time,
                "total_time_ms": total_time,
                "chunk_map": chunk_map
            }

        finally:
            store.pg_pool.disconnect() # Close the session pool

    except Exception as e:
        logger.error(f"Error during RAG generation: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "error": str(e),
            "query": query
        }

