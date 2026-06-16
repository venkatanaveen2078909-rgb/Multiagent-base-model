"""
agents/research_agent.py
Research Agent — searches the web via Tavily and produces structured, cited reports.
"""

from __future__ import annotations

import os
import time
from typing import Optional

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_tavily import TavilySearch

from config import get_settings
from .base import AgentOutput, BaseAgent


class ResearchAgent(BaseAgent):
    """Searches the web, synthesises information, and returns a structured Markdown report."""

    agent_name = "research_agent"
    version = "1.0"

    def __init__(
        self,
        prompt_version: Optional[str] = None,
        search_depth: str = "advanced",
        max_results: int = 5,
        summary_length: str = "standard",
        temperature: float = 0.1,
    ):
        super().__init__(prompt_version=prompt_version, temperature=temperature)
        self.search_depth = search_depth
        self.max_results = max_results
        self.summary_length = summary_length

    def _make_search_tool(self, depth: str, k: int) -> TavilySearch:
        settings = get_settings()
        if not settings.tavily_api_key:
            raise ValueError(
                "TAVILY_API_KEY is not configured. Add it to your .env file."
            )
        os.environ["TAVILY_API_KEY"] = settings.tavily_api_key
        return TavilySearch(
            max_results=k,
            search_depth=depth,
            include_answer=True,
            include_raw_content=False,
            include_images=False,
        )

    async def run(
        self,
        task: str,
        search_depth: Optional[str] = None,
        max_results: Optional[int] = None,
        summary_length: Optional[str] = None,
        **kwargs,
    ) -> AgentOutput:
        start = time.perf_counter()
        depth = search_depth or self.search_depth
        k = max_results or self.max_results
        length = summary_length or self.summary_length

        self.log.info("research_agent.run", task=task[:80], depth=depth, k=k)

        try:
            tool = self._make_search_tool(depth, k)

            length_hint = {
                "brief": "Keep the summary under 150 words.",
                "standard": "Write a thorough but focused summary (200-350 words).",
                "detailed": "Write a comprehensive, detailed summary (400+ words).",
            }.get(length, "")

            augmented_system = (
                self.system_prompt + f"\n\nSUMMARY LENGTH INSTRUCTION: {length_hint}"
            )

            messages = [
                SystemMessage(content=augmented_system),
                HumanMessage(content=f"Research task: {task}"),
            ]

            llm_with_tools = self.llm.bind_tools([tool])
            ai_msg = await llm_with_tools.ainvoke(messages)

            search_results = []
            tool_messages = []

            if ai_msg.tool_calls:
                for tool_call in ai_msg.tool_calls:
                    query = tool_call["args"].get("query", task)
                    self.log.debug("research_agent.search", query=query)
                    result = await tool.ainvoke({"query": query})
                    search_results.extend(result if isinstance(result, list) else [result])
                    tool_messages.append(
                        ToolMessage(content=str(result), tool_call_id=tool_call["id"])
                    )

            search_results_text = "\n\n".join([str(t.content) for t in tool_messages])
            synthesis_messages = [
                SystemMessage(content=augmented_system),
                HumanMessage(content=f"Research task: {task}\n\nHere are the search results:\n{search_results_text}"),
                HumanMessage(
                    content=(
                        "Now write the final structured research report based on "
                        "the search results above. Follow the exact output format "
                        "specified in your system instructions. DO NOT attempt to call any tools."
                    )
                )
            ]

            final = await self.llm.ainvoke(synthesis_messages)
            report = final.content

            latency = self._time_it(start)
            self.log.info("research_agent.done", latency_ms=latency)

            return AgentOutput(
                agent_name=self.agent_name,
                version=self.version,
                prompt_version=self.prompt_version,
                task=task,
                result=report,
                metadata={
                    "search_depth": depth,
                    "max_results": k,
                    "summary_length": length,
                    "sources_retrieved": len(search_results),
                    "tool_calls_made": len(ai_msg.tool_calls) if ai_msg.tool_calls else 0,
                },
                latency_ms=latency,
                success=True,
            )

        except Exception as exc:
            self.log.error("research_agent.error", error=str(exc))
            return AgentOutput(
                agent_name=self.agent_name,
                version=self.version,
                prompt_version=self.prompt_version,
                task=task,
                result="",
                latency_ms=self._time_it(start),
                success=False,
                error=str(exc),
            )
