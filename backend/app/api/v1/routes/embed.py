import logging
import torch
from typing import List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.qwen_embedder import QwenEmbedder

router = APIRouter()
logger = logging.getLogger(__name__)

_embedder = None

def get_embedder() -> QwenEmbedder:
    """
    Initializes and returns a singleton instance of QwenEmbedder.
    """
    global _embedder
    if _embedder is None:
        logger.info("Initializing QwenEmbedder...")
        try:
            _embedder = QwenEmbedder()
            logger.info("QwenEmbedder successfully initialized")
        except Exception as e:
            logger.error(f"Error during QwenEmbedder initialization: {e}")
            raise HTTPException(status_code=503, detail="Embedding service unavailable")
    return _embedder

class EmbedRequest(BaseModel):
    texts: List[str]
    max_length: int = 1024

class EmbedResponse(BaseModel):
    embeddings: List[List[float]]

@router.post("/embed", response_model=EmbedResponse)
def embed_texts(req: EmbedRequest):
    """
    Generates embeddings for a list of texts.
    
    Args:
        req: Request containing the texts to embed and the maximum length
        
    Returns:
        The normalized embeddings corresponding to the texts
        
    Raises:
        HTTPException: If an error occurs during the embedding computation
    """
    try:
        if not req.texts:
            return EmbedResponse(embeddings=[])
            
        logger.info(f"Computing embeddings for {len(req.texts)} texts")
        
        embedder = get_embedder()
        
        # Process in small batches to avoid memory issues.
        batch_size = 8
        all_embeddings = []
        
        for i in range(0, len(req.texts), batch_size):
            batch_texts = req.texts[i:i + batch_size]
            logger.debug(f"Processing batch {i//batch_size + 1} ({len(batch_texts)} texts)")
            
            batch_embeddings = embedder.embed(batch_texts, max_length=req.max_length)
            
            if hasattr(batch_embeddings, 'tolist'):
                batch_embeddings_list = batch_embeddings.tolist()
            else:
                batch_embeddings_list = batch_embeddings
                
            all_embeddings.extend(batch_embeddings_list)
            
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            
        logger.info(f"Embeddings computed: {len(all_embeddings)} vectors of dimension {len(all_embeddings[0]) if all_embeddings else 0}")
        
        return EmbedResponse(embeddings=all_embeddings)
        
    except Exception as e:
        logger.error(f"Error during embedding computation: {e}")
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        raise HTTPException(status_code=500, detail=f"Error during embedding computation: {str(e)}")