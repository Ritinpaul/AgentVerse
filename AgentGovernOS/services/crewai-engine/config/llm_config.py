"""LLM configuration with provider fallback chain.

Primary: Ollama (phi4-mini) — local, free, offline
Fallback 1: Ollama (llama3.2) — stronger reasoning
Fallback 2: OpenAI GPT-4o-mini — cloud API
Fallback 3: Anthropic Claude Haiku — cloud API

Each agent is mapped to a model tier based on task complexity.
"""

import os

from crewai import LLM


def get_llm(provider: str = "primary") -> LLM:
    """Get LLM instance by provider tier."""
    providers = {
        "primary": LLM(
            model="ollama/phi4-mini",
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            temperature=0.3,
        ),
        "fallback_1": LLM(
            model="ollama/llama3.2",
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            temperature=0.3,
        ),
        "fallback_2": LLM(
            model="openai/gpt-4o-mini",
            api_key=os.getenv("OPENAI_API_KEY", ""),
            temperature=0.2,
        ),
        "fallback_3": LLM(
            model="anthropic/claude-3-haiku-20240307",
            api_key=os.getenv("ANTHROPIC_API_KEY", ""),
            temperature=0.2,
        ),
    }
    return providers.get(provider, providers["primary"])


# Agent → Model mapping
AGENT_MODEL_MAP = {
    # Core Crew (per-dispute execution)
    "evidence_collector": "primary",
    "risk_evaluator": "fallback_1",
    "negotiation_agent": "fallback_1",
    "dispute_resolver": "fallback_1",
    "governance_sentinel": "fallback_1",  # Use fallback_2 in prod
    # Meta Crew (scheduled / trigger-based)
    "historian": "primary",
    "gene_auditor": "primary",
    "red_teamer": "fallback_1",
    "compliance_synthesizer": "fallback_1",
}


def get_agent_llm(agent_name: str) -> LLM:
    """Get the appropriate LLM for a specific agent."""
    provider = AGENT_MODEL_MAP.get(agent_name, "primary")
    return get_llm(provider)
