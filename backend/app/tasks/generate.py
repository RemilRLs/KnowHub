import logging
import dramatiq
import time 
from typing import Dict, Any, List, Optional

from dramatiq.results import Results
from dramatiq.results.backends import RedisBackend

from app.core.pgvector.pgvector import PgVectorStore
from app.config.config import PGVECTOR_DSN
from app.core.redis_config import redis_client
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
            f"[Document {i} - {source} (page {page}) - distance: {distance:.3f}]\n{text}\n"
        )
    
    return "\n---\n".join(context_parts)

def _generate_with_llm(
        query: str,
        context: str,
        max_tokens: int = 2048,
        temperature: float = 0.5
) -> str:
    """
    Generating answer using context with LLM.
    """

    prompt_builder = PromptBuilder(PromptType.RAG_GENERATION)
    messages = prompt_builder.add_variables(
        query=query,
        context=context
    ).build_messages()



    try:
        # Creation of the correct class link to the provider.

        llm = LLMFactory.create(
            provider=llm_settings.LLM_PROVIDER,
            model=llm_settings.LLM_MODEL,
            temperature=temperature,
            api_key=llm_settings.OPENAI_API_KEY if llm_settings.LLM_PROVIDER == "openai" else llm_settings.ANTHROPIC_API_KEY,
        )

        # Now we have an instance of the choosen provider (by the user).
        answer = llm.generate_chat(messages=messages)
        
        return answer
    
    except Exception as e:
        logger.error(f"LLM generation error: {str(e)}", exc_info=True)
        return f"Erreur lors de la génération de la réponse: {str(e)}"

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

            return {
                "status": "sucess",
                "query": query,
                "answer": answer,
                "sources": [chunk.get('source', 'Unknown') for chunk in retrieved_chunks],
                "retrieved_chunks": len(retrieved_chunks),
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

