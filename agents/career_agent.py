"""
agents/career_agent.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Career Agent — analyses resumes and profiles, identifies skill
gaps, and generates personalised career roadmaps.

Tunable parameters:
  - experience_level    : "student" | "junior" | "mid" | "senior"
  - career_target       : e.g. "ML Engineer", "Backend Engineer"
  - industry_focus      : e.g. "fintech", "healthtech", "AI startups"
  - recommendation_depth: "shallow" | "standard" | "deep"
"""

from __future__ import annotations

import time
from typing import Optional

from langchain_core.messages import HumanMessage, SystemMessage

from .base import AgentOutput, BaseAgent


class CareerAgent(BaseAgent):
    """
    Provides personalised career guidance including skill gap analysis
    and concrete roadmaps tailored to the user's background.
    """

    agent_name = "career_agent"
    version = "1.0"

    def __init__(
        self,
        prompt_version: Optional[str] = None,
        experience_level: str = "student",
        career_target: str = "AI/ML Engineer",
        industry_focus: str = "AI startups",
        recommendation_depth: str = "standard",
        temperature: float = 0.4,  # Slightly higher for creative roadmap generation
    ):
        super().__init__(prompt_version=prompt_version, temperature=temperature)

        self.experience_level = experience_level
        self.career_target = career_target
        self.industry_focus = industry_focus
        self.recommendation_depth = recommendation_depth

    def _build_context_block(
        self,
        experience_level: str,
        career_target: str,
        industry_focus: str,
        recommendation_depth: str,
    ) -> str:
        """Build a context block appended to the system prompt."""
        depth_instructions = {
            "shallow": "Provide a high-level overview. Keep recommendations concise.",
            "standard": "Provide a balanced, actionable analysis with specific steps.",
            "deep": (
                "Provide an exhaustive analysis. Include specific course names, "
                "project ideas, company names, and week-by-week action items where possible."
            ),
        }
        return (
            f"\n\nUSER CONTEXT:\n"
            f"- Experience Level: {experience_level}\n"
            f"- Career Target: {career_target}\n"
            f"- Industry Focus: {industry_focus}\n"
            f"- Analysis Depth: {recommendation_depth}\n"
            f"- Instruction: {depth_instructions.get(recommendation_depth, '')}"
        )

    async def run(
        self,
        task: str,
        experience_level: Optional[str] = None,
        career_target: Optional[str] = None,
        industry_focus: Optional[str] = None,
        recommendation_depth: Optional[str] = None,
        **kwargs,
    ) -> AgentOutput:
        """
        Run the career agent on a resume / profile description.

        Parameters
        ----------
        task                 : Resume text or career question.
        experience_level     : Override student/junior/mid/senior.
        career_target        : Override the target role.
        industry_focus       : Override the target industry.
        recommendation_depth : Override shallow/standard/deep.
        """
        start = time.perf_counter()

        exp   = experience_level    or self.experience_level
        target = career_target      or self.career_target
        ind   = industry_focus      or self.industry_focus
        depth = recommendation_depth or self.recommendation_depth

        self.log.info(
            "career_agent.run",
            experience=exp,
            target=target,
            industry=ind,
            depth=depth,
        )

        try:
            context_block = self._build_context_block(exp, target, ind, depth)
            augmented_system = self.system_prompt + context_block

            messages = [
                SystemMessage(content=augmented_system),
                HumanMessage(
                    content=(
                        f"Please analyse the following profile and provide career guidance:\n\n"
                        f"{task}"
                    )
                ),
            ]

            response = await self.llm.ainvoke(messages)
            result = response.content

            latency = self._time_it(start)
            self.log.info("career_agent.done", latency_ms=latency)

            return AgentOutput(
                agent_name=self.agent_name,
                version=self.version,
                prompt_version=self.prompt_version,
                task=task[:200] + "..." if len(task) > 200 else task,
                result=result,
                metadata={
                    "experience_level": exp,
                    "career_target": target,
                    "industry_focus": ind,
                    "recommendation_depth": depth,
                },
                latency_ms=latency,
                success=True,
            )

        except Exception as exc:
            self.log.error("career_agent.error", error=str(exc))
            return AgentOutput(
                agent_name=self.agent_name,
                version=self.version,
                prompt_version=self.prompt_version,
                task=task[:200],
                result="",
                latency_ms=self._time_it(start),
                success=False,
                error=str(exc),
            )