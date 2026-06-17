"""
src/graphrag/retrievers/arxiv_retriever.py

Hybrid arXiv retriever: live API search + Qdrant semantic cache.

Flow
----
1. Query arXiv API for fresh papers matching the medical topic.
2. Optionally cache paper embeddings into Qdrant 'arxiv_papers' collection.
3. On subsequent queries, also search the Qdrant cache for older cached papers.
4. Return merged, deduplicated results with full metadata.

Each result dict contains:
    arxiv_id    : str   — e.g. "2301.07041"
    title       : str
    authors     : list[str]
    summary     : str   — abstract (first 500 chars)
    published   : str   — ISO date string
    url         : str   — direct arXiv link (https://arxiv.org/abs/<id>)
    topics      : list[str] — primary category tags
    source      : str   — "arxiv_api" | "qdrant_cache"
"""

import sys
import os
import hashlib
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
))))

import arxiv
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct,
)

from src.config import config
from src.embeddings.regolo_embedder import get_regolo_embedder


class ArxivRetriever:
    """
    Hybrid arXiv retriever combining live API queries with a Qdrant vector cache.

    Parameters
    ----------
    qdrant_client : QdrantClient | None
        Shared Qdrant client. Creates a new one if not provided.
    gemini_client : genai.Client | None
        Shared Gemini client for embedding. Creates one if not provided.
    max_results : int
        Maximum papers to fetch from arXiv API per query.
    cache_enabled : bool
        Whether to embed and store papers in Qdrant for reuse.
    """

    def __init__(
        self,
        qdrant_client: QdrantClient | None = None,
        max_results: int | None = None,
        cache_enabled: bool | None = None,
    ):
        self.qdrant = qdrant_client or QdrantClient(
            host=config.QDRANT_HOST, port=config.QDRANT_PORT
        )
        self.embedder = get_regolo_embedder()
        self.max_results = max_results if max_results is not None else config.ARXIV_MAX_RESULTS
        self.cache_enabled = cache_enabled if cache_enabled is not None else config.ARXIV_CACHE_ENABLED
        self.collection    = config.COLLECTION_ARXIV

        if self.cache_enabled:
            self._ensure_collection()

    # ── Qdrant collection setup ───────────────────────────────────────────────

    def _ensure_collection(self) -> None:
        """Create the arxiv_papers Qdrant collection if it does not exist."""
        existing = [c.name for c in self.qdrant.get_collections().collections]
        if self.collection not in existing:
            self.qdrant.create_collection(
                collection_name=self.collection,
                vectors_config=VectorParams(
                    size=config.EMBEDDING_DIM,
                    distance=Distance.COSINE,
                ),
            )

    # ── Embedding ─────────────────────────────────────────────────────────────

    def _embed(self, text: str) -> list[float]:
        return self.embedder.embed(text)

    # ── arXiv API search ──────────────────────────────────────────────────────

    def _search_arxiv_api(self, query: str) -> list[dict]:
        """Fetch papers from the live arXiv API."""
        client = arxiv.Client()
        search = arxiv.Search(
            query=query,
            max_results=self.max_results,
            sort_by=arxiv.SortCriterion.Relevance,
        )

        papers = []
        for result in client.results(search):
            paper = {
                "arxiv_id":  result.entry_id.split("/")[-1],
                "title":     result.title,
                "authors":   [a.name for a in result.authors],
                "summary":   result.summary[:500].replace("\n", " "),
                "published": result.published.strftime("%Y-%m-%d") if result.published else "",
                "url":       result.entry_id,
                "topics":    result.categories,
                "source":    "arxiv_api",
            }
            papers.append(paper)

            # Cache in Qdrant if enabled
            if self.cache_enabled:
                self._cache_paper(paper)

        return papers

    # ── Qdrant cache operations ───────────────────────────────────────────────

    def _paper_to_point_id(self, arxiv_id: str) -> int:
        """Convert arxiv_id string to a stable integer Qdrant point ID."""
        return int(hashlib.md5(arxiv_id.encode()).hexdigest()[:8], 16)

    def _cache_paper(self, paper: dict) -> None:
        """Embed paper title+abstract and upsert into Qdrant cache."""
        try:
            text_to_embed = f"{paper['title']}. {paper['summary']}"
            vector = self._embed(text_to_embed)
            point_id = self._paper_to_point_id(paper["arxiv_id"])

            self.qdrant.upsert(
                collection_name=self.collection,
                points=[
                    PointStruct(
                        id=point_id,
                        vector=vector,
                        payload={
                            "arxiv_id":  paper["arxiv_id"],
                            "title":     paper["title"],
                            "authors":   paper["authors"],
                            "summary":   paper["summary"],
                            "published": paper["published"],
                            "url":       paper["url"],
                            "topics":    paper["topics"],
                        },
                    )
                ],
            )
        except Exception:
            # Cache failure should never break the main query
            pass

    def _search_qdrant_cache(self, query: str, top_k: int = 3) -> list[dict]:
        """Search the Qdrant arxiv_papers cache for semantically similar papers."""
        try:
            vector = self._embed(query)
            hits = self.qdrant.search(
                collection_name=self.collection,
                query_vector=vector,
                limit=top_k,
                with_payload=True,
            )
            results = []
            for hit in hits:
                p = hit.payload
                p["source"] = "qdrant_cache"
                p["score"]  = round(hit.score, 4)
                results.append(p)
            return results
        except Exception:
            return []

    # ── Public API ────────────────────────────────────────────────────────────

    def search(self, query: str) -> list[dict]:
        """
        Hybrid search: live arXiv API + Qdrant cache.

        Returns a deduplicated, merged list of paper dicts sorted by recency
        (API results first, then cache-only extras).
        """
        # 1. Live arXiv API
        api_results = self._search_arxiv_api(query)

        # 2. Qdrant cache (only if collection has points)
        cache_results: list[dict] = []
        if self.cache_enabled:
            cache_results = self._search_qdrant_cache(query, top_k=3)

        # 3. Deduplicate: prefer API result if same arxiv_id
        seen_ids: set[str] = {p["arxiv_id"] for p in api_results}
        for p in cache_results:
            if p.get("arxiv_id") not in seen_ids:
                api_results.append(p)
                seen_ids.add(p["arxiv_id"])

        return api_results

    def format_for_display(self, papers: list[dict]) -> str:
        """
        Return a compact human-readable string of paper results
        (used as the tool output returned to the LLM).
        """
        if not papers:
            return "No arXiv papers found for this query."

        lines = []
        for i, p in enumerate(papers, 1):
            authors = ", ".join(p.get("authors", [])[:3])
            if len(p.get("authors", [])) > 3:
                authors += " et al."
            lines.append(
                f"{i}. [{p.get('published', '')}] {p.get('title', 'N/A')}\n"
                f"   Authors : {authors}\n"
                f"   Topics  : {', '.join(p.get('topics', []))}\n"
                f"   Summary : {p.get('summary', '')[:200]}...\n"
                f"   URL     : {p.get('url', '')}\n"
                f"   Source  : {p.get('source', '')}"
            )
        return "\n\n".join(lines)
