"""
src/embeddings/regolo_embedder.py

Regolo-based embedder using Qwen3-Embedding-8B model.

Replaces the previous Gemini-based embedder with Regolo API for semantic embeddings.
"""

import os
import json
from typing import Optional
import httpx
import time

from src.config import config


class RegloEmbedder:
    """
    Embedding client for Regolo API using Qwen3-Embedding-8B model.
    
    Supports batch embeddings with automatic retry on rate limits.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: int = 300,
    ):
        """
        Initialize Regolo embedder.
        
        Parameters
        ----------
        api_key : str, optional
            Regolo API key. Defaults to REGOLO_API_KEY from config.
        api_base_url : str, optional
            Regolo API base URL. Defaults to REGOLO_API_BASE_URL from config.
        model : str, optional
            Embedding model name. Defaults to EMBEDDING_MODEL from config.
        timeout : int
            Request timeout in seconds. Default 300.
        """
        self.api_key = api_key or config.REGOLO_API_KEY
        self.api_base_url = api_base_url or config.REGOLO_API_BASE_URL
        self.model = model or config.EMBEDDING_MODEL
        self.timeout = timeout
        
        if not self.api_key:
            raise ValueError("REGOLO_API_KEY not set. Please configure it in .env")
        
        self.client = httpx.Client(
            timeout=timeout,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
        )
    
    def embed(self, text: str) -> list[float]:
        """
        Generate a single embedding vector.
        
        Parameters
        ----------
        text : str
            Text to embed
            
        Returns
        -------
        list[float]
            Embedding vector
        """
        return self.embed_batch([text])[0]
    
    def embed_batch(
        self,
        texts: list[str],
        max_retries: int = 5,
    ) -> list[list[float]]:
        """
        Generate embeddings for a batch of texts using Regolo API.
        
        Parameters
        ----------
        texts : list[str]
            Batch of texts to embed
        max_retries : int
            Maximum number of retries on rate limit (429)
            
        Returns
        -------
        list[list[float]]
            List of embedding vectors
            
        Raises
        ------
        Exception
            If embedding fails after max retries
        """
        url = f"{self.api_base_url}/embeddings"
        
        for attempt in range(max_retries):
            try:
                payload = {
                    "model": self.model,
                    "input": texts,
                }
                
                response = self.client.post(url, json=payload)
                
                if response.status_code == 200:
                    data = response.json()
                    # Extract embeddings from response
                    embeddings = [item["embedding"] for item in data["data"]]
                    return embeddings
                
                elif response.status_code == 429 and attempt < max_retries - 1:
                    # Rate limited - wait and retry
                    wait_time = 65  # Standard rate limit wait
                    print(
                        f"\n  ⏱️  Rate limited (429). "
                        f"Waiting {wait_time}s before retry {attempt + 1}/{max_retries - 1}..."
                    )
                    time.sleep(wait_time)
                    
                else:
                    error_msg = f"Embedding request failed: {response.status_code}"
                    try:
                        error_data = response.json()
                        if "error" in error_data:
                            error_msg += f" - {error_data['error']}"
                    except:
                        error_msg += f" - {response.text}"
                    raise Exception(error_msg)
                    
            except Exception as exc:
                if "429" in str(exc) and attempt < max_retries - 1:
                    wait_time = 65
                    print(
                        f"\n  ⏱️  Rate limited (429). "
                        f"Waiting {wait_time}s before retry {attempt + 1}/{max_retries - 1}..."
                    )
                    time.sleep(wait_time)
                else:
                    raise
        
        raise Exception(f"Failed to get embeddings after {max_retries} retries")
    
    def close(self):
        """Close the HTTP client."""
        self.client.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


def get_regolo_embedder() -> RegloEmbedder:
    """
    Create and return a Regolo embedder instance.
    
    Returns
    -------
    RegloEmbedder
        Configured embedder using Qwen3-Embedding-8B
    """
    return RegloEmbedder()


# Legacy function for backward compatibility
def create_embedding(text: str) -> list[float]:
    """
    Generate a single embedding using Regolo API.
    
    Parameters
    ----------
    text : str
        Text to embed
        
    Returns
    -------
    list[float]
        Embedding vector
    """
    with get_regolo_embedder() as embedder:
        return embedder.embed(text)


def create_embeddings_batch(
    texts: list[str],
    max_retries: int = 5,
) -> list[list[float]]:
    """
    Generate embeddings for a batch of texts.
    
    Parameters
    ----------
    texts : list[str]
        Batch of texts to embed
    max_retries : int
        Maximum number of retries on rate limit
        
    Returns
    -------
    list[list[float]]
        List of embedding vectors
    """
    with get_regolo_embedder() as embedder:
        return embedder.embed_batch(texts, max_retries=max_retries)
