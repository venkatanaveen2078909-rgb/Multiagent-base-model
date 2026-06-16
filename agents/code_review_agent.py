"""
agents/code_review_agent.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Code Review Agent — performs multi-dimensional code review
covering correctness, performance, security, and style.

Tunable parameters:
  - strictness_level: "lenient" | "standard" | "strict"
  - security_focus  : bool
  - performance_focus: bool
  - explanation_detail: "minimal" | "standard" | "verbose"
  - language        : "python" | "javascript" | "cpp" | "auto"
"""

from __future__ import annotations

import re
import time
from typing import Optional

from langchain_core.messages import HumanMessage, SystemMessage

from .base import AgentOutput, BaseAgent


class CodeReviewAgent(BaseAgent):
    """
    Performs production-grade code review across multiple quality dimensions.
    """

    agent_name = "code_review_agent"
    version = "1.0"

    def __init__(
        self,
        prompt_version: Optional[str] = None,
        strictness_level: str = "standard",
        security_focus: bool = True,
        performance_focus: bool = True,
        explanation_detail: str = "standard",
        temperature: float = 0.1,  # Very low for deterministic reviews
    ):
        super().__init__(prompt_version=prompt_version, temperature=temperature)

        self.strictness_level = strictness_level
        self.security_focus = security_focus
        self.performance_focus = performance_focus
        self.explanation_detail = explanation_detail

    @staticmethod
    def _detect_language(code: str) -> str:
        """Heuristic language detection from code content."""
        if re.search(r"\bdef \w+\(|import \w+|print\(", code):
            return "Python"
        if re.search(r"function \w+\(|const |let |var ", code):
            return "JavaScript"
        if re.search(r"#include|int main\(|std::", code):
            return "C++"
        return "Unknown"

    def _build_review_context(
        self,
        language: str,
        strictness: str,
        security: bool,
        performance: bool,
        detail: str,
    ) -> str:
        """Build the configuration block appended to the system prompt."""
        focus_areas = []
        if security:
            focus_areas.append("Pay special attention to security vulnerabilities.")
        if performance:
            focus_areas.append("Pay special attention to performance bottlenecks.")

        strictness_map = {
            "lenient": "Focus only on critical bugs and major issues. Ignore minor style issues.",
            "standard": "Review all quality dimensions with balanced coverage.",
            "strict": (
                "Apply the highest standards. Flag all issues including minor style, "
                "naming conventions, and theoretical edge cases."
            ),
        }

        detail_map = {
            "minimal": "Keep explanations brief — 1-2 sentences per issue.",
            "standard": "Provide clear explanations with context.",
            "verbose": "Provide comprehensive explanations with examples, alternatives, and learning context.",
        }

        return (
            f"\n\nREVIEW CONFIGURATION:\n"
            f"- Language: {language}\n"
            f"- Strictness: {strictness} — {strictness_map.get(strictness, '')}\n"
            f"- Explanation Detail: {detail} — {detail_map.get(detail, '')}\n"
            + ("\n".join(f"- {f}" for f in focus_areas) if focus_areas else "")
        )

    async def run(
        self,
        task: str,
        strictness_level: Optional[str] = None,
        security_focus: Optional[bool] = None,
        performance_focus: Optional[bool] = None,
        explanation_detail: Optional[str] = None,
        language: Optional[str] = None,
        **kwargs,
    ) -> AgentOutput:
        """
        Run the code review agent on provided code.

        Parameters
        ----------
        task              : The code to review (plain string).
        strictness_level  : Override lenient/standard/strict.
        security_focus    : Override security focus flag.
        performance_focus : Override performance focus flag.
        explanation_detail: Override minimal/standard/verbose.
        language          : Override language hint (or "auto" for detection).
        """
        start = time.perf_counter()

        strict  = strictness_level  or self.strictness_level
        sec     = security_focus    if security_focus is not None else self.security_focus
        perf    = performance_focus if performance_focus is not None else self.performance_focus
        detail  = explanation_detail or self.explanation_detail

        # Auto-detect language if not provided
        detected_lang = language or self._detect_language(task)

        self.log.info(
            "code_review_agent.run",
            language=detected_lang,
            strictness=strict,
            code_length=len(task),
        )

        try:
            context = self._build_review_context(
                detected_lang, strict, sec, perf, detail
            )
            augmented_system = self.system_prompt + context

            messages = [
                SystemMessage(content=augmented_system),
                HumanMessage(
                    content=(
                        f"Please review the following {detected_lang} code:\n\n"
                        f"```{detected_lang.lower()}\n{task}\n```"
                    )
                ),
            ]

            response = await self.llm.ainvoke(messages)
            result = response.content

            latency = self._time_it(start)
            self.log.info("code_review_agent.done", latency_ms=latency)

            return AgentOutput(
                agent_name=self.agent_name,
                version=self.version,
                prompt_version=self.prompt_version,
                task=f"Code review ({detected_lang}, {len(task)} chars)",
                result=result,
                metadata={
                    "language": detected_lang,
                    "strictness_level": strict,
                    "security_focus": sec,
                    "performance_focus": perf,
                    "explanation_detail": detail,
                    "code_length": len(task),
                },
                latency_ms=latency,
                success=True,
            )

        except Exception as exc:
            self.log.error("code_review_agent.error", error=str(exc))
            return AgentOutput(
                agent_name=self.agent_name,
                version=self.version,
                prompt_version=self.prompt_version,
                task="Code review failed",
                result="",
                latency_ms=self._time_it(start),
                success=False,
                error=str(exc),
            )