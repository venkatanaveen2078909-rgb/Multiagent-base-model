"""
agents/evaluator_agent.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Evaluator Agent — assesses outputs from any other agent against
standardised quality metrics and generates a certification report.

Metrics:
  Accuracy (0-10) | Completeness (0-10) | Relevance (0-10)
  Structure (0-10) | Tool Usage Quality (0-10)
  Hallucination Risk (Low/Medium/High)
  Overall Score (0-100)
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Optional

from langchain_core.messages import HumanMessage, SystemMessage

from .base import AgentOutput, BaseAgent


@dataclass
class EvaluationResult:
    """Parsed, machine-readable evaluation scores."""
    agent_evaluated: str
    prompt_version: str
    accuracy: float
    completeness: float
    relevance: float
    structure: float
    tool_usage_quality: float
    hallucination_risk: str        # "Low" | "Medium" | "High"
    overall_score: float           # 0-100
    certification_status: str      # "PASS" | "CONDITIONAL PASS" | "FAIL"
    strengths: str
    weaknesses: str
    raw_report: str
    latency_ms: float


class EvaluatorAgent(BaseAgent):
    """
    Evaluates any AgentOutput and produces a structured EvaluationResult
    plus a human-readable certification report.
    """

    agent_name = "evaluator_agent"
    version = "1.0"
    PASS_THRESHOLD = 70.0

    def __init__(
        self,
        prompt_version: Optional[str] = None,
        temperature: float = 0.1,  # Low for consistent scoring
    ):
        super().__init__(prompt_version=prompt_version, temperature=temperature)

    # ──────────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────────

    async def evaluate(self, agent_output: AgentOutput) -> EvaluationResult:
        """
        Evaluate an AgentOutput from any agent.

        Returns a structured EvaluationResult with scores and certification.
        """
        start = time.perf_counter()
        self.log.info(
            "evaluator_agent.evaluate",
            target_agent=agent_output.agent_name,
        )

        try:
            eval_request = self._build_eval_request(agent_output)

            messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=eval_request),
            ]

            response = await self.llm.ainvoke(messages)
            raw_report = response.content

            latency = self._time_it(start)
            parsed = self._parse_scores(raw_report, agent_output.agent_name)
            parsed["latency_ms"] = latency
            parsed["raw_report"] = raw_report
            parsed["agent_evaluated"] = agent_output.agent_name
            parsed["prompt_version"] = agent_output.prompt_version

            # Determine certification status
            score = parsed["overall_score"]
            if score >= self.PASS_THRESHOLD:
                status = "PASS" if score >= 80 else "CONDITIONAL PASS"
            else:
                status = "FAIL"
            parsed["certification_status"] = status

            self.log.info(
                "evaluator_agent.done",
                score=score,
                status=status,
                latency_ms=latency,
            )

            return EvaluationResult(**parsed)

        except Exception as exc:
            self.log.error("evaluator_agent.error", error=str(exc))
            return EvaluationResult(
                agent_evaluated=agent_output.agent_name,
                prompt_version=agent_output.prompt_version,
                accuracy=0,
                completeness=0,
                relevance=0,
                structure=0,
                tool_usage_quality=0,
                hallucination_risk="High",
                overall_score=0,
                certification_status="FAIL",
                strengths="",
                weaknesses=f"Evaluation failed: {exc}",
                raw_report="",
                latency_ms=self._time_it(start),
            )

    # Also satisfy the base class abstract method
    async def run(self, task: str, **kwargs) -> AgentOutput:
        """
        Thin wrapper — evaluator primarily used via evaluate().
        Accepts a raw text output for evaluation without a full AgentOutput.
        """
        start = time.perf_counter()
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=f"Evaluate the following output:\n\n{task}"),
        ]
        response = await self.llm.ainvoke(messages)
        return AgentOutput(
            agent_name=self.agent_name,
            version=self.version,
            prompt_version=self.prompt_version,
            task="Direct evaluation",
            result=response.content,
            latency_ms=self._time_it(start),
            success=True,
        )

    # ──────────────────────────────────────────────────────────────────────────
    # Private helpers
    # ──────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _build_eval_request(output: AgentOutput) -> str:
        """Format the evaluation request prompt."""
        return (
            f"Please evaluate the following agent output:\n\n"
            f"**Agent:** {output.agent_name}\n"
            f"**Prompt Version:** {output.prompt_version}\n"
            f"**Task:** {output.task}\n"
            f"**Latency:** {output.latency_ms}ms\n"
            f"**Success:** {output.success}\n\n"
            f"**Output:**\n{output.result}\n\n"
            f"Provide a comprehensive evaluation following your output format exactly."
        )

    @staticmethod
    def _parse_scores(report: str, agent_name: str) -> dict:
        """
        Parse numerical scores from the evaluation report.
        Robust to slight formatting variation.
        """
        def extract_score(pattern: str, default: float = 5.0) -> float:
            m = re.search(pattern, report, re.IGNORECASE)
            if m:
                try:
                    return min(10.0, max(0.0, float(m.group(1))))
                except ValueError:
                    pass
            return default

        def extract_risk(default: str = "Medium") -> str:
            m = re.search(
                r"hallucination\s+risk[^\w]*(low|medium|high)", report, re.IGNORECASE
            )
            return m.group(1).capitalize() if m else default

        def extract_overall(default: float = 50.0) -> float:
            # Look for "Overall Score: 85/100" or "Overall Score: 85"
            m = re.search(
                r"overall\s+score[^\d]*(\d+(?:\.\d+)?)\s*(?:/\s*100)?",
                report,
                re.IGNORECASE,
            )
            if m:
                return min(100.0, max(0.0, float(m.group(1))))
            # Fallback: compute from sub-scores
            return default

        def extract_section(header: str) -> str:
            m = re.search(
                rf"##\s*{re.escape(header)}\s*\n(.*?)(?=\n##|\Z)",
                report,
                re.IGNORECASE | re.DOTALL,
            )
            return m.group(1).strip() if m else ""

        accuracy   = extract_score(r"accuracy[^\d]*(\d+(?:\.\d+)?)\s*/\s*10")
        completeness = extract_score(r"completeness[^\d]*(\d+(?:\.\d+)?)\s*/\s*10")
        relevance  = extract_score(r"relevance[^\d]*(\d+(?:\.\d+)?)\s*/\s*10")
        structure  = extract_score(r"structure[^\d]*(\d+(?:\.\d+)?)\s*/\s*10")
        tool_q     = extract_score(r"tool\s+usage\s+quality[^\d]*(\d+(?:\.\d+)?)\s*/\s*10")
        risk       = extract_risk()

        # Compute overall if not explicit
        overall = extract_overall()
        if overall == 50.0:  # Default not matched — compute
            overall = round(
                (accuracy + completeness + relevance + structure + tool_q) * 2, 1
            )
            risk_penalty = {"Low": 0, "Medium": 5, "High": 15}.get(risk, 5)
            overall = max(0.0, overall - risk_penalty)

        return {
            "accuracy": accuracy,
            "completeness": completeness,
            "relevance": relevance,
            "structure": structure,
            "tool_usage_quality": tool_q,
            "hallucination_risk": risk,
            "overall_score": overall,
            "strengths": extract_section("Strengths"),
            "weaknesses": (
                extract_section("Areas for Improvement")
                or extract_section("Weaknesses")
            ),
        }