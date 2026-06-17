"""
api/dependencies.py

Singleton FastAPI dependencies for shared database clients.
Uses lru_cache to ensure a single instance per process lifetime.
"""

import sys
import os
from functools import lru_cache

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.graphrag.retrievers.graph_retriever import GraphRetriever
from src.graphrag.retrievers.vector_retriever import VectorRetriever
from src.graphrag.retrievers.arxiv_retriever import ArxivRetriever
from src.graphrag.medical_graphrag import MedicalGraphRAG
from src.graphrag.orchestrator import MedicalGraphRAGOrchestrator


@lru_cache(maxsize=1)
def get_graph_retriever() -> GraphRetriever:
    return GraphRetriever()


@lru_cache(maxsize=1)
def get_vector_retriever() -> VectorRetriever:
    return VectorRetriever()


@lru_cache(maxsize=1)
def get_arxiv_retriever() -> ArxivRetriever:
    return ArxivRetriever()


@lru_cache(maxsize=1)
def get_medical_graphrag() -> MedicalGraphRAG:
    return MedicalGraphRAG()


@lru_cache(maxsize=1)
def get_orchestrator() -> MedicalGraphRAGOrchestrator:
    return MedicalGraphRAGOrchestrator()
