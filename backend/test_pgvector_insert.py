#!/usr/bin/env python3
"""
Test simple pour vérifier l'insertion de chunks dans PgVector
"""

import os
from dotenv import load_dotenv
from langchain_core.documents import Document

from app.core.pgvector import PgVectorStore

def test_insert_chunks():
    load_dotenv()
    
    # Configuration de la base de données
    dsn = f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@localhost:5433/{os.getenv('POSTGRES_DB')}"
    
    # Création du store
    pgvector_store = PgVectorStore(dsn)
    
    # Documents de test avec différentes sources
    test_docs = [
        Document(
            page_content="Ceci est le premier chunk du document A",
            metadata={"file_name": "document_A.pdf", "page": 1, "author": "Auteur A"}
        ),
        Document(
            page_content="Ceci est le second chunk du document A", 
            metadata={"file_name": "document_A.pdf", "page": 2, "author": "Auteur A"}
        ),
        Document(
            page_content="Ceci est le premier chunk du document B",
            metadata={"file_name": "document_B.pdf", "page": 1, "author": "Auteur B"}
        ),
        Document(
            page_content="Ceci est le second chunk du document B",
            metadata={"file_name": "document_B.pdf", "page": 2, "author": "Auteur B"}
        ),
    ]
    
    collection_name = "test_collection"
    
    print("=== Test d'insertion initiale ===")
    pgvector_store.insert_chunks(test_docs, collection_name)
    
    print("\n=== Test de réinsertion (doit être skippé) ===") 
    pgvector_store.insert_chunks(test_docs, collection_name)
    
    print("\n=== Test avec nouveau document ===")
    new_docs = [
        Document(
            page_content="Nouveau chunk du document C",
            metadata={"file_name": "document_C.pdf", "page": 1, "author": "Auteur C"}
        )
    ]
    pgvector_store.insert_chunks(new_docs, collection_name)
    
    # Nettoyage
    pgvector_store.close_connection()
    print("\nTest terminé!")

if __name__ == "__main__":
    test_insert_chunks()