import time
import hashlib
import re
import google.generativeai as genai
from typing import List
from langchain_core.embeddings import Embeddings
from app.core.config import settings

class GeminiRESTEmbeddings(Embeddings):
    """Custom LangChain-compatible embeddings class that calls Google Gemini
    via the REST-based google-generativeai SDK, completely bypassing gRPC."""

    def __init__(self, api_key: str, model: str = "models/gemini-embedding-001"):
        self.model = model
        genai.configure(api_key=api_key)

    def _embed_with_retry(self, text: str, max_retries: int = 3) -> List[float]:
        """Embed a single text with retry logic."""
        for attempt in range(max_retries):
            try:
                result = genai.embed_content(
                    model=self.model,
                    content=text,
                    task_type="retrieval_document"
                )
                return result["embedding"]
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    print(f"  Embedding retry {attempt + 1}/{max_retries} after error: {e}")
                    time.sleep(wait_time)
                else:
                    raise

    def _embed_batch_with_retry(self, texts: List[str], max_retries: int = 3) -> List[List[float]]:
        """Embed a list of texts in a single batch call with retry logic."""
        if not texts:
            return []
            
        for attempt in range(max_retries):
            try:
                # If only one text is passed, optimize for it
                if len(texts) == 1:
                    return [self._embed_with_retry(texts[0])]
                    
                result = genai.embed_content(
                    model=self.model,
                    content=texts,
                    task_type="retrieval_document"
                )
                
                embeddings = result["embedding"]
                if embeddings and isinstance(embeddings[0], dict):
                    return [emb["values"] for emb in embeddings]
                return embeddings
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = 3 ** attempt
                    print(f"  Batch embedding retry {attempt + 1}/{max_retries} after error: {e}")
                    time.sleep(wait_time)
                else:
                    print("  Batch embedding failed. Falling back to one-by-one embedding with rate throttling...")
                    fallback_embeddings = []
                    for text in texts:
                        fallback_embeddings.append(self._embed_with_retry(text))
                        time.sleep(0.5)  # 0.5 seconds sleep between requests to stay under 100 RPM
                    return fallback_embeddings

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of documents in batches via REST API to minimize API rate limit hits."""
        return self._embed_batch_with_retry(texts)

    def embed_query(self, text: str) -> List[float]:
        """Embed a single query via REST API."""
        result = genai.embed_content(
            model=self.model,
            content=text,
            task_type="retrieval_query"
        )
        return result["embedding"]


class LocalHashEmbeddings(Embeddings):
    """Offline embeddings that keep ingest/search working without API quota.
    
    Uses a deterministic bag-of-tokens hashing approach.
    """

    def __init__(self, dimensions: int = 384):
        self.dimensions = dimensions

    def _embed(self, text: str) -> List[float]:
        vector = [0.0] * self.dimensions
        tokens = re.findall(r"[A-Za-z_][A-Za-z0-9_]*|/[A-Za-z0-9_./-]+", text.lower())

        for token in tokens:
            digest = hashlib.md5(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign

        norm = sum(value * value for value in vector) ** 0.5
        if norm:
            vector = [value / norm for value in vector]
        return vector

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> List[float]:
        return self._embed(text)


def get_embeddings_provider():
    """Factory function returning the configured embeddings provider."""
    provider = settings.EMBEDDING_PROVIDER.lower()
    api_key = settings.GEMINI_API_KEY

    if provider == "gemini" and api_key and api_key != "your_gemini_api_key_here":
        print("Using Google Gemini REST Embeddings.")
        return GeminiRESTEmbeddings(
            api_key=api_key,
            model=settings.GEMINI_EMBEDDING_MODEL
        )
    
    print("Using Local Bag-of-Tokens Hash Embeddings (Offline Mode).")
    return LocalHashEmbeddings()
