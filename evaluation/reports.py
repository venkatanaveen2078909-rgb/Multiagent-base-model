"""
evaluation/reports.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Report generation:
  - CertificationReport : Per-agent pass/fail certificate
  - TuningReport        : Prompt version comparison
  - BenchmarkReport     : Aggregated benchmark results
  - EvalSummaryReport   : Full platform health snapshot
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


# ─────────────────────────────────────────────────────────────────────────────
# Data Classes
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class CertificationReport:
    """
    Certification status for a single agent at a specific prompt version.
    Printed / serialised for audit purposes.
    """
    agent_name: str
    agent_version: str
    prompt_version: str
    accuracy: float
    completion_rate: float
    hallucination_risk: str
    overall_score: float
    certification_status: str   # PASS | CONDITIONAL PASS | FAIL
    test_cases_run: int
    test_cases_passed: int
    generated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    @property
    def pass_rate(self) -> float:
        if self.test_cases_run == 0:
            return 0.0
        return round(self.test_cases_passed / self.test_cases_run * 100, 1)

    def to_markdown(self) -> str:
        status_icon = {"PASS": "✅", "CONDITIONAL PASS": "⚠️", "FAIL": "❌"}.get(
            self.certification_status, "❓"
        )
        return (
            f"# Certification Report\n\n"
            f"## {self.agent_name} {self.agent_version}\n\n"
            f"| Field | Value |\n"
            f"|-------|-------|\n"
            f"| Agent | {self.agent_name} |\n"
            f"| Version | {self.agent_version} |\n"
            f"| Prompt Version | {self.prompt_version} |\n"
            f"| Accuracy | {self.accuracy}% |\n"
            f"| Completion Rate | {self.completion_rate}% |\n"
            f"| Hallucination Risk | {self.hallucination_risk} |\n"
            f"| Overall Score | {self.overall_score}/100 |\n"
            f"| Test Cases | {self.test_cases_passed}/{self.test_cases_run} ({self.pass_rate}%) |\n"
            f"| Generated | {self.generated_at} |\n\n"
            f"## Certification Status\n\n"
            f"### {status_icon} {self.certification_status}\n"
        )

    def to_dict(self) -> Dict:
        return {
            "agent_name": self.agent_name,
            "agent_version": self.agent_version,
            "prompt_version": self.prompt_version,
            "accuracy": self.accuracy,
            "completion_rate": self.completion_rate,
            "hallucination_risk": self.hallucination_risk,
            "overall_score": self.overall_score,
            "certification_status": self.certification_status,
            "test_cases_run": self.test_cases_run,
            "test_cases_passed": self.test_cases_passed,
            "pass_rate": self.pass_rate,
            "generated_at": self.generated_at,
        }


@dataclass
class TuningReport:
    """
    Comparison between two prompt versions for the same agent.
    Shows which version performs better and by how much.
    """
    agent_name: str
    version_a: str
    version_b: str
    metrics_a: Dict[str, float]
    metrics_b: Dict[str, float]
    generated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def _delta(self, metric: str) -> float:
        return round(self.metrics_b.get(metric, 0) - self.metrics_a.get(metric, 0), 2)

    def to_markdown(self) -> str:
        metrics = ["accuracy", "completeness", "relevance", "structure",
                   "tool_usage_quality", "overall_score"]

        rows = []
        for m in metrics:
            a = self.metrics_a.get(m, 0)
            b = self.metrics_b.get(m, 0)
            delta = self._delta(m)
            trend = "⬆️" if delta > 0 else ("⬇️" if delta < 0 else "➡️")
            rows.append(f"| {m.replace('_', ' ').title()} | {a} | {b} | {trend} {delta:+.2f} |")

        overall_winner = (
            self.version_b if self._delta("overall_score") > 0
            else (self.version_a if self._delta("overall_score") < 0 else "Tie")
        )

        return (
            f"# Prompt Tuning Report — {self.agent_name}\n\n"
            f"Comparing **{self.version_a}** vs **{self.version_b}**\n\n"
            f"| Metric | {self.version_a} | {self.version_b} | Delta |\n"
            f"|--------|{'|'.join(['-'*10]*3)}|\n"
            + "\n".join(rows)
            + f"\n\n**Winner:** {overall_winner}\n\n"
            f"*Generated: {self.generated_at}*\n"
        )


@dataclass
class BenchmarkRunResult:
    """Result for a single benchmark test case."""
    agent: str
    category: str
    input_summary: str
    passed: bool
    score: float
    missing_keywords: List[str]
    latency_ms: float


@dataclass
class BenchmarkReport:
    """Aggregated results across all benchmark test cases for one agent."""
    agent_name: str
    prompt_version: str
    results: List[BenchmarkRunResult] = field(default_factory=list)
    generated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def pass_rate(self) -> float:
        return round(self.passed / self.total * 100, 1) if self.total else 0.0

    @property
    def avg_score(self) -> float:
        if not self.results:
            return 0.0
        return round(sum(r.score for r in self.results) / self.total, 1)

    @property
    def avg_latency(self) -> float:
        if not self.results:
            return 0.0
        return round(sum(r.latency_ms for r in self.results) / self.total, 1)

    def by_category(self) -> Dict[str, Dict]:
        cats: Dict[str, list] = {}
        for r in self.results:
            cats.setdefault(r.category, []).append(r)
        return {
            cat: {
                "total": len(items),
                "passed": sum(1 for i in items if i.passed),
                "pass_rate": round(sum(1 for i in items if i.passed) / len(items) * 100, 1),
            }
            for cat, items in cats.items()
        }

    def to_markdown(self) -> str:
        cat_rows = "\n".join(
            f"| {cat} | {v['total']} | {v['passed']} | {v['pass_rate']}% |"
            for cat, v in sorted(self.by_category().items())
        )
        return (
            f"# Benchmark Report — {self.agent_name}\n\n"
            f"Prompt Version: **{self.prompt_version}**\n\n"
            f"## Summary\n\n"
            f"| Metric | Value |\n"
            f"|--------|-------|\n"
            f"| Total Test Cases | {self.total} |\n"
            f"| Passed | {self.passed} |\n"
            f"| Pass Rate | {self.pass_rate}% |\n"
            f"| Average Score | {self.avg_score}/100 |\n"
            f"| Average Latency | {self.avg_latency}ms |\n\n"
            f"## Results by Category\n\n"
            f"| Category | Total | Passed | Pass Rate |\n"
            f"|----------|-------|--------|-----------|\n"
            + cat_rows
            + f"\n\n*Generated: {self.generated_at}*\n"
        )


@dataclass
class EvalSummaryReport:
    """Full platform health snapshot across all agents."""
    certifications: List[CertificationReport] = field(default_factory=list)
    generated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_markdown(self) -> str:
        rows = []
        for c in self.certifications:
            status_icon = {"PASS": "✅", "CONDITIONAL PASS": "⚠️", "FAIL": "❌"}.get(
                c.certification_status, "❓"
            )
            rows.append(
                f"| {c.agent_name} | {c.prompt_version} | "
                f"{c.accuracy}% | {c.completion_rate}% | "
                f"{c.hallucination_risk} | {c.overall_score}/100 | "
                f"{status_icon} {c.certification_status} |"
            )

        return (
            f"# Agentic AI Platform — Evaluation Summary\n\n"
            f"*Generated: {self.generated_at}*\n\n"
            f"| Agent | Prompt | Accuracy | Completion | Hallucination | Score | Status |\n"
            f"|-------|--------|----------|------------|---------------|-------|--------|\n"
            + "\n".join(rows)
        )

    def to_json(self) -> str:
        return json.dumps(
            {"generated_at": self.generated_at,
             "agents": [c.to_dict() for c in self.certifications]},
            indent=2,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Report Factory
# ─────────────────────────────────────────────────────────────────────────────

def generate_certification(
    agent_name: str,
    agent_version: str,
    prompt_version: str,
    eval_results: List[Any],  # List[EvaluationResult]
) -> CertificationReport:
    """
    Build a CertificationReport from a list of EvaluationResult objects.
    Typically called after running benchmark test cases.
    """
    if not eval_results:
        return CertificationReport(
            agent_name=agent_name,
            agent_version=agent_version,
            prompt_version=prompt_version,
            accuracy=0.0,
            completion_rate=0.0,
            hallucination_risk="High",
            overall_score=0.0,
            certification_status="FAIL",
            test_cases_run=0,
            test_cases_passed=0,
        )

    scores = [r.overall_score for r in eval_results]
    accuracies = [r.accuracy * 10 for r in eval_results]  # Convert 0-10 → 0-100

    risks = [r.hallucination_risk for r in eval_results]
    risk_counts = {"Low": risks.count("Low"), "Medium": risks.count("Medium"), "High": risks.count("High")}
    dominant_risk = max(risk_counts, key=risk_counts.get)

    avg_score = round(sum(scores) / len(scores), 1)
    avg_accuracy = round(sum(accuracies) / len(accuracies), 1)
    passed = sum(1 for r in eval_results if r.certification_status in ("PASS", "CONDITIONAL PASS"))
    completion_rate = round(passed / len(eval_results) * 100, 1)

    if avg_score >= 80 and completion_rate >= 80:
        status = "PASS"
    elif avg_score >= 65 and completion_rate >= 65:
        status = "CONDITIONAL PASS"
    else:
        status = "FAIL"

    return CertificationReport(
        agent_name=agent_name,
        agent_version=agent_version,
        prompt_version=prompt_version,
        accuracy=avg_accuracy,
        completion_rate=completion_rate,
        hallucination_risk=dominant_risk,
        overall_score=avg_score,
        certification_status=status,
        test_cases_run=len(eval_results),
        test_cases_passed=passed,
    )


def generate_tuning_report(
    agent_name: str,
    version_a: str,
    metrics_a: Dict[str, float],
    version_b: str,
    metrics_b: Dict[str, float],
) -> TuningReport:
    return TuningReport(
        agent_name=agent_name,
        version_a=version_a,
        version_b=version_b,
        metrics_a=metrics_a,
        metrics_b=metrics_b,
    )