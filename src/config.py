"""
src/config.py

Centralised configuration loaded from environment variables.
All modules import from here instead of reading .env directly.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = PROJECT_ROOT / ".env"

load_dotenv(dotenv_path=ENV_PATH)


def normalise_litellm_model(model: str) -> str:
    """Map repo aliases onto LiteLLM-supported provider prefixes."""
    if not model:
        return model

    provider, separator, model_name = model.partition("/")
    if separator and provider.lower() == "regolo":
        return f"openai/{model_name}"
    return model


class Config:
    # ── Regolo (active) ───────────────────────────────────────────────────────
    REGOLO_API_KEY: str    = os.getenv("REGOLO_API_KEY", "")
    REGOLO_API_BASE_URL: str = os.getenv(
        "REGOLO_API_BASE_URL", "https://api.regolo.ai/v1"
    )

    # Multiple Regolo Models
    REGOLO_MODEL_PRIMARY: str  = os.getenv("REGOLO_MODEL_PRIMARY", "Llama-3.3-70B-Instruct")
    REGOLO_MODEL_FAST: str     = os.getenv("REGOLO_MODEL_FAST", "qwen3.5-9b")
    REGOLO_MODEL_MEDICAL: str  = os.getenv("REGOLO_MODEL_MEDICAL", "Llama-3.3-70B-Instruct")
    REGOLO_MODEL_CODING: str   = os.getenv("REGOLO_MODEL_CODING", "qwen3-coder-next")
    REGOLO_MODEL_ADVANCED: str = os.getenv("REGOLO_MODEL_ADVANCED", "mistral-small-4-119b")
    REGOLO_MODEL_EMBEDDING: str = os.getenv("REGOLO_MODEL_EMBEDDING", "Qwen3-Embedding-8B")
    REGOLO_MODEL: str          = os.getenv("REGOLO_MODEL", "Llama-3.3-70B-Instruct")

    # Model selection strategy
    MODEL_SELECTION_STRATEGY: str = os.getenv("MODEL_SELECTION_STRATEGY", "primary")

    # Embedding configuration
    EMBEDDING_MODEL: str   = os.getenv("EMBEDDING_MODEL", "Qwen3-Embedding-8B")
    EMBEDDING_DIM: int     = int(os.getenv("EMBEDDING_DIM", "4096"))  # Qwen3-Embedding-8B actual output dim
    LLM_MODEL: str         = os.getenv("LLM_MODEL", "Llama-3.3-70B-Instruct")
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0"))

    # ── LiteLLM (provider-agnostic router) ───────────────────────────────────
    # LITELLM_MODEL format: "<provider>/<model>"
    # For Regolo, use openai/<model> because LiteLLM routes it as an OpenAI-compatible endpoint.
    # Legacy regolo/<model> values are still accepted and normalised by LiteLLMClient.
    # e.g. openai/Llama-3.3-70B-Instruct | gemini/gemini-2.0-flash |
    #      openai/gpt-4o-mini | anthropic/claude-3-5-haiku-20241022
    LITELLM_MODEL: str     = normalise_litellm_model(
        os.getenv("LITELLM_MODEL", "openai/Llama-3.3-70B-Instruct")
    )
    LITELLM_MAX_TOOL_CALLS: int = int(os.getenv("LITELLM_MAX_TOOL_CALLS", "6"))

    # ── Gemini (commented, preserved for reference) ───────────────────────────
    # GEMINI_API_KEY: str    = os.getenv("GEMINI_API_KEY", "")
    # EMBEDDING_MODEL: str   = os.getenv("EMBEDDING_MODEL", "models/gemini-embedding-001")
    # EMBEDDING_DIM: int     = int(os.getenv("EMBEDDING_DIM", "3072"))

    # ── Neo4j ─────────────────────────────────────────────────────────────────
    # Note: If Neo4j is running via docker-compose and you run this app outside the
    # docker network, keep localhost. If the app itself runs inside docker-compose,
    # use service name `neo4j` instead.
    NEO4J_URI: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USER: str     = os.getenv("NEO4J_USER", "neo4j")

    NEO4J_PASSWORD: str = os.getenv("NEO4J_PASSWORD", "Neo4j@123")

    # ── Qdrant ────────────────────────────────────────────────────────────────
    QDRANT_HOST: str      = os.getenv("QDRANT_HOST", "localhost")
    QDRANT_PORT: int      = int(os.getenv("QDRANT_PORT", "6333"))
    QDRANT_GRPC_PORT: int = int(os.getenv("QDRANT_GRPC_PORT", "6334"))

    # ── Qdrant collection names ───────────────────────────────────────────────
    COLLECTION_PATIENTS:   str = "medical_patients"
    COLLECTION_DRUGS:      str = "medical_drugs"
    COLLECTION_CONDITIONS: str = "medical_conditions"
    COLLECTION_ARXIV:      str = "arxiv_papers"       # arXiv paper cache

    # ── arXiv retrieval ───────────────────────────────────────────────────────
    ARXIV_MAX_RESULTS: int = int(os.getenv("ARXIV_MAX_RESULTS", "5"))
    ARXIV_CACHE_ENABLED: bool = os.getenv("ARXIV_CACHE_ENABLED", "true").lower() == "true"

    # ── LiteLLM client configuration ──────────────────────────────────────────
    # Set api_base for Regolo
    LITELLM_API_BASE: str  = os.getenv("LITELLM_API_BASE", "https://api.regolo.ai/v1")

    # ── Data generation ───────────────────────────────────────────────────────
    NUM_PATIENTS:   int = int(os.getenv("NUM_PATIENTS", "1000"))
    NUM_DRUGS:      int = int(os.getenv("NUM_DRUGS", "80"))
    NUM_CONDITIONS: int = int(os.getenv("NUM_CONDITIONS", "60"))
    NUM_PROVIDERS:  int = int(os.getenv("NUM_PROVIDERS", "50"))

    @classmethod
    def get_model(cls, task: str = "default") -> str:
        """
        Get the appropriate Regolo model for a specific task.

        Parameters
        ----------
        task : str
            Task type: "default", "primary", "fast", "medical", "reasoning",
            "summarization", "coding", "analysis", "extraction", "advanced"

        Returns
        -------
        str
            Model name (e.g., "Llama-3.3-70B-Instruct")

        Available Models
        ----------------
        - Llama-3.3-70B-Instruct: Complex reasoning, medical analysis
        - qwen3.5-9b: Fast, lightweight tasks
        - qwen3-coder-next: Code analysis and generation
        - mistral-small-4-119b: Advanced reasoning
        - Qwen3-Embedding-8B: Semantic embeddings
        """
        task_to_model = {
            "default": cls.REGOLO_MODEL_PRIMARY,
            "primary": cls.REGOLO_MODEL_PRIMARY,      # Complex reasoning
            "fast": cls.REGOLO_MODEL_FAST,            # Quick tasks (qwen3.5-9b)
            "medical": cls.REGOLO_MODEL_MEDICAL,      # Medical domain
            "reasoning": cls.REGOLO_MODEL_PRIMARY,    # Deep reasoning
            "summarization": cls.REGOLO_MODEL_FAST,   # Quick summarization
            "analysis": cls.REGOLO_MODEL_PRIMARY,     # Medical analysis
            "extraction": cls.REGOLO_MODEL_FAST,      # Info extraction
            "coding": cls.REGOLO_MODEL_CODING,        # Code tasks (qwen3-coder-next)
            "advanced": cls.REGOLO_MODEL_ADVANCED,    # Advanced reasoning (mistral)
            "embedding": cls.REGOLO_MODEL_EMBEDDING,  # Semantic embeddings
        }
        return task_to_model.get(task.lower(), cls.REGOLO_MODEL_PRIMARY)

    @classmethod
    def get_litellm_model(cls, task: str | None = None, model: str | None = None) -> str:
        """Return a LiteLLM-safe model string for a task or explicit model."""
        if model:
            return normalise_litellm_model(model)
        if task:
            return f"openai/{cls.get_model(task)}"
        return cls.LITELLM_MODEL


config = Config()
