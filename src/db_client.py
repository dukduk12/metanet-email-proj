import chromadb
from loguru import logger
from google import genai
from src.config import settings
from typing import List, Dict, Any

class ChromaClient:
    def __init__(self, collection_name="email_collection"):
        try:
            import os
            host = os.getenv("CHROMA_HOST", "localhost")
            self.client = chromadb.HttpClient(host=host, port=8000)
            logger.info(f"Connected to ChromaDB HTTP at {host}:8000")
            self.collection = self.client.get_or_create_collection(name=collection_name)
        except Exception as e:
            logger.error(f"Failed to connect to ChromaDB: {e}")
            self.collection = None

    def embed_text(self, text: str) -> List[float]:
        try:
            gemini_client = genai.Client(api_key=settings.gemini_api_key)
            result = gemini_client.models.embed_content(
                model="gemini-embedding-2",
                contents=text
            )
            return result.embeddings[0].values
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return []

    def add_email(self, email_id: str, title: str, summary: str, date: str, sender: str):
        if not self.collection:
            logger.warning("Chroma collection not available. Skipping add_email.")
            return False
            
        doc_text = f"제목: {title}\n요약: {summary}"
        embedding = self.embed_text(doc_text)
        
        if not embedding:
            logger.error(f"Failed to generate embedding for email {email_id}")
            return False
            
        try:
            self.collection.add(
                ids=[email_id],
                embeddings=[embedding],
                documents=[doc_text],
                metadatas=[{"title": title, "date": date, "sender": sender, "summary": summary}]
            )
            logger.info(f"Successfully added email {email_id} to ChromaDB")
            return True
        except Exception as e:
            logger.error(f"Error adding to ChromaDB: {e}")
            return False

    def query_similar(self, text: str, n_results: int = 3) -> List[Dict[str, Any]]:
        if not self.collection:
            return []
            
        embedding = self.embed_text(text)
        if not embedding:
            return []
            
        try:
            results = self.collection.query(
                query_embeddings=[embedding],
                n_results=n_results
            )
            
            matched_items = []
            if results['ids'] and results['ids'][0]:
                for i in range(len(results['ids'][0])):
                    matched_items.append({
                        "id": results['ids'][0][i],
                        "document": results['documents'][0][i],
                        "metadata": results['metadatas'][0][i],
                        "distance": results['distances'][0][i] if 'distances' in results and results['distances'] else 0.0
                    })
            return matched_items
        except Exception as e:
            logger.error(f"Error querying ChromaDB: {e}")
            return []
