"""
src/graphrag/orchestrator.py

Agentic orchestrator using LangChain for structured tool-calling and reasoning.

Flow
----
1. Build LangChain ReAct agent and tools.
2. Send user query to LangChain AgentExecutor.
3. Agent loops over GraphTraversal / SemanticSearch / ArxivSearch tools.
4. Tool executions accumulate context results.
5. Return final agent output.
6. Fuse accumulated results → generate grounded answer via GraphAwareGenerator.

To switch providers, change only LITELLM_MODEL in .env:
  gemini/gemini-2.0-flash           → current default (uses GEMINI_API_KEY)
  openai/gpt-4o-mini                → needs OPENAI_API_KEY
  anthropic/claude-3-5-haiku-20241022 → needs ANTHROPIC_API_KEY
"""

import sys
import os
import json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.config import config
from src.llm.litellm_client import LiteLLMClient
from src.graphrag.retrievers.graph_retriever import GraphRetriever
from src.graphrag.retrievers.vector_retriever import VectorRetriever
from src.graphrag.retrievers.arxiv_retriever import ArxivRetriever
from src.graphrag.fusion import ResultFusion
from src.graphrag.generator import GraphAwareGenerator

# LangChain Agent Imports
from langchain_community.chat_models import ChatLiteLLM
from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.prompts import PromptTemplate
from langchain_core.tools import Tool

# Unused OpenAI-format schemas and prompts removed in favor of LangChain native constructs.


class MedicalGraphRAGOrchestrator:
    """
    LangChain-powered agentic orchestrator.

    Uses LangChain's AgentExecutor to run a ReAct agent that loops through
    hybrid retrieval tools before returning a final grounded answer.

    Tools exposed to the LLM
    ------------------------
    - GraphTraversal  : Neo4j Cypher-based graph retrieval
    - SemanticSearch  : Qdrant vector similarity search
    - ArxivSearch     : arXiv research paper retrieval
    """

    def __init__(self):
        self.graph_retriever  = GraphRetriever()
        self.vector_retriever = VectorRetriever()
        self.generator        = GraphAwareGenerator()
        self.fusion           = ResultFusion()

        # Initialize LiteLLMClient to load and normalize configuration & credentials
        self.lite_client = LiteLLMClient()

        # arXiv retriever
        self.arxiv_retriever = ArxivRetriever()

        # Accumulated context from tool calls (reset per query)
        self._graph_results:  list[dict] = []
        self._vector_results: list[dict] = []
        self._arxiv_results:  list[dict] = []

        print(f"[Orchestrator] LiteLLM model: {self.lite_client.model}")

        # Inject normalized API keys/bases into env for LangChain/LiteLLM to read
        if self.lite_client.api_key:
            if self.lite_client.provider == "openai" or self.lite_client.provider_alias == "regolo":
                os.environ["OPENAI_API_KEY"] = self.lite_client.api_key
            elif self.lite_client.provider == "gemini":
                os.environ["GEMINI_API_KEY"] = self.lite_client.api_key
            elif self.lite_client.provider == "anthropic":
                os.environ["ANTHROPIC_API_KEY"] = self.lite_client.api_key
        
        if self.lite_client.api_base:
            if self.lite_client.provider == "openai" or self.lite_client.provider_alias == "regolo":
                os.environ["OPENAI_API_BASE"] = self.lite_client.api_base

        # Configure LangChain ChatLiteLLM wrapper
        self.chat_model = ChatLiteLLM(
            model=self.lite_client.model,
            temperature=config.LLM_TEMPERATURE
        )

        # Map existing pipeline tools to LangChain Tool structures
        self.tools = [
            Tool(
                name="GraphTraversal",
                func=self._graph_tool,
                description=(
                    "Query the Neo4j medical knowledge graph. Use this to find: "
                    "high-risk patients on 3+ interacting drugs, drug interaction chains, "
                    "contraindicated medications, or patient cohorts sharing doctors/conditions. "
                    "Input should be a description of the pattern or patient query."
                )
            ),
            Tool(
                name="SemanticSearch",
                func=self._vector_tool,
                description=(
                    "Search patient profiles, drug documents, and condition descriptions "
                    "using semantic vector similarity in Qdrant. Use for fuzzy matching, "
                    "finding similar patient cases, or background knowledge about a drug/condition. "
                    "Input should be the search query."
                )
            ),
            Tool(
                name="ArxivSearch",
                func=self._arxiv_tool,
                description=(
                    "Search arXiv for relevant medical research papers. Use this to find "
                    "recent publications, clinical studies, drug research, or condition "
                    "guidelines related to the query. Input should be the medical topic to search."
                )
            )
        ]

        # Define ReAct agent prompt forcing graph validation
        template = """You are a medical knowledge assistant with access to a hybrid retrieval system.

CRITICAL RULE: You MUST call the GraphTraversal tool at least ONCE before answering.
Graph traversal provides verified, structured facts. SemanticSearch provides semantic context.
When you have gathered enough context from both tools, provide a comprehensive answer that cites graph paths for every specific claim.

You have access to the following tools:

{tools}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!

Question: {input}
Thought: I should start by checking the graph for structured relationships.
{agent_scratchpad}"""

        self.prompt = PromptTemplate.from_template(template)

        # Initialize ReAct Agent and Executor
        self.agent = create_react_agent(self.chat_model, self.tools, self.prompt)
        self.executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            verbose=True,
            max_iterations=config.LITELLM_MAX_TOOL_CALLS,
            return_intermediate_steps=True,
            handle_parsing_errors=True
        )

    # ─── Tool implementations (unchanged business logic) ──────────────────────

    def _graph_tool(self, query_description: str) -> str:
        """
        Dispatch graph queries based on the plain-English description the LLM sends.
        Returns JSON string of results and accumulates into self._graph_results.
        """
        q = query_description.lower()

        if any(kw in q for kw in ["high risk", "interact", "dangerous", "3+"]):
            results = self.graph_retriever.find_high_risk_patients(limit=8)
        elif any(kw in q for kw in ["contraindic"]):
            results = self.graph_retriever.find_patients_with_contraindicated_drugs(limit=8)
        elif any(kw in q for kw in ["shared doctor", "cohort", "same doctor"]):
            results = self.graph_retriever.find_shared_doctor_cohorts(limit=5)
        elif any(kw in q for kw in ["warfarin", "aspirin", "metformin", "hop", "chain"]):
            drug = "Warfarin"
            for d in ["Warfarin", "Aspirin", "Metformin", "Lisinopril", "Digoxin"]:
                if d.lower() in q:
                    drug = d
                    break
            results = self.graph_retriever.k_hop_drug_interactions(drug, k=2)
        elif any(kw in q for kw in ["diabetes", "hypertension", "kidney", "heart"]):
            cond_map = {
                "diabetes":     ["Type 2 Diabetes", "Type 1 Diabetes"],
                "hypertension": ["Hypertension"],
                "kidney":       ["Chronic Kidney Disease"],
                "heart":        ["Heart Failure", "Coronary Artery Disease"],
            }
            conditions = []
            for kw, names in cond_map.items():
                if kw in q:
                    conditions.extend(names)
            results = self.graph_retriever.find_patients_with_conditions(conditions, limit=8)
        else:
            results = self.graph_retriever.find_high_risk_patients(limit=8)

        self._graph_results.extend(results if isinstance(results, list) else [results])
        return json.dumps(results, indent=2, default=str)

    def _vector_tool(self, query: str) -> str:
        """
        Run Qdrant vector search and accumulate results into self._vector_results.
        """
        results = self.vector_retriever.search_all(query, top_k=5)
        self._vector_results.extend(results.get("patients", []))
        return json.dumps(results, indent=2, default=str)

    def _arxiv_tool(self, query: str) -> str:
        """
        Search arXiv for research papers and accumulate into self._arxiv_results.
        Returns formatted string for the LLM to read.
        """
        papers = self.arxiv_retriever.search(query)
        self._arxiv_results.extend(papers)
        return self.arxiv_retriever.format_for_display(papers)

    # ─── LangChain Agentic execution loop ─────────────────────────────────────

    def _run_tool_loop(self, user_query: str) -> str:
        """
        Runs the LangChain Agent Executor and formats intermediate steps for logging.
        """
        response = self.executor.invoke({
            "input": user_query
        })
        
        # Format logs to mimic raw agent thoughts & actions
        steps_log = []
        for idx, (action, observation) in enumerate(response.get("intermediate_steps", [])):
            steps_log.append(f"Thought: {action.log}")
            # Truncate long observations in logs to avoid huge output blocks
            obs_str = str(observation)
            if len(obs_str) > 800:
                obs_str = obs_str[:800] + "\n... [TRUNCATED FOR LOGS]"
            steps_log.append(f"Observation: {obs_str}\n")
            
        steps_log.append(f"Final Answer: {response['output']}")
        return "\n".join(steps_log)

    # ─── Public API ───────────────────────────────────────────────────────────

    def query(self, natural_language_query: str) -> dict:
        """
        Run the full agentic GraphRAG pipeline:
        1. LiteLLM tool-calling loop (graph first enforced by system prompt).
        2. Fuse accumulated graph + vector results.
        3. Generate grounded answer via GraphAwareGenerator.

        Returns
        -------
        dict with keys: query, answer, provenance, confidence, agent_output
        """
        # Reset accumulated context for this query
        self._graph_results  = []
        self._vector_results = []
        self._arxiv_results  = []

        # Run the agentic loop — populates _graph_results and _vector_results
        agent_text = self._run_tool_loop(natural_language_query)

        # Fuse graph + vector results
        fused = ResultFusion.fuse(self._graph_results, self._vector_results)

        # Generate final grounded answer
        final = self.generator.generate_answer(natural_language_query, fused)
        final["agent_output"] = agent_text
        final["arxiv_papers"] = self._arxiv_results
        return final
