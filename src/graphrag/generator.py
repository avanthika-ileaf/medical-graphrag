"""
src/graphrag/generator.py

Grounded answer generation with graph path citations.
Uses LiteLLM (Regolo by default) for provider-agnostic generation.
Produces structured responses including evidence provenance.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.config import config
from src.llm.litellm_client import LiteLLMClient
from src.graphrag.fusion import ResultFusion

SYSTEM_PROMPT = """You are a medical knowledge assistant with access to a hybrid knowledge graph and vector database.

CRITICAL RULES:
1. ALWAYS base your answer on the provided context — never invent patient data.
2. Cite graph paths for every specific claim using the format:
   [Graph: Patient→Drug→INTERACTS_WITH→Drug]  or  [Vector: score=0.92]
3. If graph facts contradict semantic matches, trust the graph.
4. State your confidence level explicitly.
5. Never disclose raw patient names without flagging that this is synthetic data.

Output format:
ANSWER: <direct answer to the query>
EVIDENCE: <list of supporting facts with citations>
CONFIDENCE: <high | medium | low> — <reason>
LIMITATIONS: <what the system cannot determine from available data>
"""

USER_PROMPT_TEMPLATE = """
Query: {query}

Retrieved Context:
{context}

Generate a comprehensive medical answer with full provenance tracing.
"""


class GraphAwareGenerator:
    """Generate grounded answers with graph path citations."""

    def __init__(self):
        # Uses LiteLLM — provider controlled by LITELLM_MODEL in .env
        # Default: openai/Llama-3.3-70B-Instruct for Regolo's OpenAI-compatible API
        self.llm = LiteLLMClient()
        self.model_name = config.LITELLM_MODEL

    def generate_answer(self, query: str, fused_context: dict) -> dict:
        """
        Generate a grounded answer from fused graph + vector context.

        Returns
        -------
        dict with keys: answer, provenance, confidence, raw_context
        """
        context_str = ResultFusion.build_context_string(fused_context)

        user_prompt = USER_PROMPT_TEMPLATE.format(
            query=query,
            context=context_str,
        )

        # LiteLLM call — works with Regolo, OpenAI, Anthropic, etc.
        response = self.llm.chat(messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_prompt},
        ])
        answer_text = response.text

        return {
            "query":       query,
            "answer":      answer_text,
            "provenance":  fused_context.get("provenance", {}),
            "confidence":  fused_context.get("confidence", 0.0),
            "raw_context": fused_context,
            "model":       self.model_name,
            "tokens_used": None,
        }

    def generate_comparison_answer(
        self,
        query: str,
        graph_context: list[dict],
        vector_context: list[dict],
    ) -> dict:
        """
        Generate separate answers from graph-only and vector-only context
        to illustrate the difference between Standard RAG and GraphRAG.
        """
        # Vector-only answer (Standard RAG simulation)
        vector_only_context = {
            "graph_facts": [],
            "semantic_matches": vector_context,
            "confirmed_patients": [],
            "provenance": {
                "graph_only": [],
                "vector_only": [r.get("patientID", "") for r in vector_context],
                "confirmed": [],
            },
            "confidence": 0.5,
        }
        standard_answer = self.generate_answer(query, vector_only_context)

        # Full GraphRAG answer
        from src.graphrag.fusion import ResultFusion
        full_context = ResultFusion.fuse(graph_context, vector_context)
        graph_rag_answer = self.generate_answer(query, full_context)

        return {
            "query":           query,
            "standard_rag":    standard_answer,
            "graph_rag":       graph_rag_answer,
        }
