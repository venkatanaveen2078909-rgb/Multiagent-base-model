"""
agents/base.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Abstract base class for all agents.

Every agent:
  - Gets a configured ChatGroq LLM.
  - Has a structured logger.
  - Exposes a run(task, **kwargs) coroutine.
  - Returns an AgentOutput dataclass.
"""

from __future__ import annotations

import abc
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

import structlog
from langchain_groq import ChatGroq

from config import get_settings
from prompts.prompt_registry import PromptRegistry

logger = structlog.get_logger()
_registry = PromptRegistry()


@dataclass
class AgentOutput:
    """Standardised output returned by every agent."""
    agent_name: str
    version: str
    prompt_version: str
    task: str
    result: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    latency_ms: float = 0.0
    success: bool = True
    error: Optional[str] = None


class BaseAgent(abc.ABC):
    """
    Abstract base class for all agents.

    Subclasses must implement:
      - agent_name: str  (class attribute)
      - _build_chain()   (returns a LangChain runnable)
      - run(task, **kwargs) -> AgentOutput
    """

    agent_name: str = "base_agent"
    version: str = "1.0"

    def __init__(
        self,
        prompt_version: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ):
        settings = get_settings()

        # Allow per-agent temperature overrides (useful for tuning)
        self.llm = ChatGroq(
            api_key=settings.groq_api_key,
            model=settings.groq_model,
            temperature=temperature or settings.groq_temperature,
            max_tokens=max_tokens or settings.groq_max_tokens,
        )

        # Fetch the versioned prompt
        self.prompt_record = _registry.get(self.agent_name, prompt_version)
        self.log = structlog.get_logger().bind(agent=self.agent_name)

    @property
    def prompt_version(self) -> str:
        return self.prompt_record.version

    @property
    def system_prompt(self) -> str:
        return self.prompt_record.system_prompt

    def _time_it(self, start: float) -> float:
        return round((time.perf_counter() - start) * 1000, 2)

    @abc.abstractmethod
    async def run(self, task: str, **kwargs) -> AgentOutput:
        """Execute the agent on the given task."""
        ...