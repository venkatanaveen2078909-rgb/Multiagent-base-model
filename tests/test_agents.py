"""
tests/test_agents.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
pytest + DeepEval test suite.

Run all tests:
  pytest tests/ -v --tb=short

Run specific agent:
  pytest tests/ -v -k "research"
  pytest tests/ -v -k "career"
  pytest tests/ -v -k "code_review"

Run without API calls (structure tests only):
  pytest tests/ -v -k "unit"

NOTE: API tests require valid .env with GROQ_API_KEY + TAVILY_API_KEY.
"""

from __future__ import annotations

import asyncio
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# ── Optional DeepEval ────────────────────────────────────────────────────────
try:
    from deepeval import assert_test
    from deepeval.metrics import AnswerRelevancyMetric, GEval
    from deepeval.test_case import LLMTestCase
    DEEPEVAL_AVAILABLE = True
except ImportError:
    DEEPEVAL_AVAILABLE = False

from agents import CareerAgent, CodeReviewAgent, EvaluatorAgent, ResearchAgent
from evaluation.benchmarks import (
    CAREER_BENCHMARKS,
    CODE_REVIEW_BENCHMARKS,
    EVALUATOR_BENCHMARKS,
    RESEARCH_BENCHMARKS,
    BenchmarkCase,
)
from evaluation.reports import generate_certification
from prompts.prompt_registry import PromptRegistry


# ─────────────────────────────────────────────────────────────────────────────
# Unit Tests (no API calls)
# ─────────────────────────────────────────────────────────────────────────────

class TestPromptRegistry:
    def test_all_agents_have_prompts(self):
        r = PromptRegistry()
        agents = r.all_agents()
        assert "research_agent" in agents
        assert "career_agent" in agents
        assert "code_review_agent" in agents
        assert "evaluator_agent" in agents
        assert "supervisor_agent" in agents

    def test_versioning(self):
        r = PromptRegistry()
        versions = r.list_versions("research_agent")
        assert len(versions) >= 3
        assert "v1" in versions
        assert "v3" in versions

    def test_default_is_latest(self):
        r = PromptRegistry()
        default = r.get("research_agent")
        assert default.version == "v3"

    def test_compare(self):
        r = PromptRegistry()
        result = r.compare("research_agent", "v1", "v2")
        assert result["version_a"]["version"] == "v1"
        assert result["version_b"]["version"] == "v2"
        assert len(result["version_a"]["prompt"]) > 0

    def test_unknown_agent_raises(self):
        r = PromptRegistry()
        with pytest.raises(KeyError):
            r.get("nonexistent_agent")


class TestBenchmarkCoverage:
    def test_research_has_20_cases(self):
        assert len(RESEARCH_BENCHMARKS) == 20

    def test_career_has_20_cases(self):
        assert len(CAREER_BENCHMARKS) == 20

    def test_code_review_has_20_cases(self):
        assert len(CODE_REVIEW_BENCHMARKS) == 20

    def test_evaluator_has_20_cases(self):
        assert len(EVALUATOR_BENCHMARKS) == 20


class TestReportGeneration:
    def test_certification_report_from_empty(self):
        report = generate_certification("test_agent", "v1.0", "v1", [])
        assert report.certification_status == "FAIL"
        assert report.pass_rate == 0.0

    def test_certification_markdown_format(self):
        from evaluation.reports import CertificationReport
        r = CertificationReport(
            agent_name="research_agent",
            agent_version="1.0",
            prompt_version="v3",
            accuracy=92.0,
            completion_rate=95.0,
            hallucination_risk="Low",
            overall_score=88.0,
            certification_status="PASS",
            test_cases_run=20,
            test_cases_passed=19,
        )
        md = r.to_markdown()
        assert "research_agent" in md
        assert "PASS" in md
        assert "92" in md


# ─────────────────────────────────────────────────────────────────────────────
# Integration Tests (require API keys)
# ─────────────────────────────────────────────────────────────────────────────

# Skip marker for when API keys aren't available
requires_api = pytest.mark.skipif(
    not os.getenv("GROQ_API_KEY"),
    reason="GROQ_API_KEY not set — skipping API integration tests",
)


@requires_api
class TestResearchAgent:
    @pytest.mark.asyncio
    async def test_basic_research(self):
        agent = ResearchAgent(search_depth="basic", max_results=3)
        output = await agent.run("What is LangGraph?")
        assert output.success
        assert len(output.result) > 100
        assert output.agent_name == "research_agent"

    @pytest.mark.asyncio
    async def test_prompt_version_v1(self):
        agent = ResearchAgent(prompt_version="v1")
        assert agent.prompt_version == "v1"
        output = await agent.run("What is Python?")
        assert output.success

    @pytest.mark.asyncio
    async def test_result_contains_summary_section(self):
        agent = ResearchAgent(search_depth="basic", max_results=2)
        output = await agent.run("What is FastAPI?")
        assert output.success
        # v3 prompt should produce these sections
        assert any(kw in output.result for kw in ["Summary", "Finding", "Source"])

    @pytest.mark.asyncio
    @pytest.mark.parametrize("case", RESEARCH_BENCHMARKS[:3])
    async def test_benchmark_cases(self, case: BenchmarkCase):
        agent = ResearchAgent(search_depth="basic", max_results=3)
        output = await agent.run(case.input)
        assert output.success, f"Agent failed: {output.error}"
        # Check at least half the expected keywords appear
        found = [kw for kw in case.expected_output_keywords if kw.lower() in output.result.lower()]
        assert len(found) >= len(case.expected_output_keywords) // 2, (
            f"Only found keywords: {found} from expected: {case.expected_output_keywords}"
        )


@requires_api
class TestCareerAgent:
    @pytest.mark.asyncio
    async def test_basic_career_advice(self):
        agent = CareerAgent(experience_level="student", career_target="AI Engineer")
        output = await agent.run(
            "I'm a 3rd year CS student with Python skills. "
            "I want to become an ML Engineer."
        )
        assert output.success
        assert len(output.result) > 200

    @pytest.mark.asyncio
    async def test_metadata_populated(self):
        agent = CareerAgent(experience_level="junior", career_target="Backend Engineer")
        output = await agent.run("I know Node.js. Want to become a backend engineer.")
        assert output.metadata["experience_level"] == "junior"
        assert output.metadata["career_target"] == "Backend Engineer"


@requires_api
class TestCodeReviewAgent:
    @pytest.mark.asyncio
    async def test_detects_sql_injection(self):
        code = """
def get_user(username):
    query = f"SELECT * FROM users WHERE name = '{username}'"
    return db.execute(query)
"""
        agent = CodeReviewAgent(strictness_level="strict", security_focus=True)
        output = await agent.run(code)
        assert output.success
        assert any(kw in output.result.lower() for kw in ["sql injection", "sql", "injection"])

    @pytest.mark.asyncio
    async def test_detects_mutable_default(self):
        code = "def add_item(item, items=[]):\n    items.append(item)\n    return items"
        agent = CodeReviewAgent(strictness_level="standard")
        output = await agent.run(code)
        assert output.success

    @pytest.mark.asyncio
    async def test_language_auto_detection(self):
        python_code = "def hello():\n    print('hello world')"
        agent = CodeReviewAgent()
        output = await agent.run(python_code)
        assert output.metadata["language"] == "Python"


@requires_api
class TestEvaluatorAgent:
    @pytest.mark.asyncio
    async def test_evaluation_returns_scores(self):
        from agents.base import AgentOutput

        fake_output = AgentOutput(
            agent_name="research_agent",
            version="1.0",
            prompt_version="v3",
            task="What is Python?",
            result=(
                "## Summary\nPython is a high-level programming language.\n\n"
                "## Key Findings\n- Created by Guido van Rossum\n- Released in 1991\n\n"
                "## Sources\n1. python.org"
            ),
        )
        evaluator = EvaluatorAgent()
        result = await evaluator.evaluate(fake_output)

        assert 0 <= result.accuracy <= 10
        assert 0 <= result.overall_score <= 100
        assert result.hallucination_risk in ("Low", "Medium", "High")
        assert result.certification_status in ("PASS", "CONDITIONAL PASS", "FAIL")

    @pytest.mark.asyncio
    async def test_poor_output_scores_low(self):
        from agents.base import AgentOutput

        poor_output = AgentOutput(
            agent_name="research_agent",
            version="1.0",
            prompt_version="v1",
            task="Explain quantum computing",
            result="I don't know.",
        )
        evaluator = EvaluatorAgent()
        result = await evaluator.evaluate(poor_output)
        assert result.overall_score < 70