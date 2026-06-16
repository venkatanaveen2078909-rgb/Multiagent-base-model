"""
graph/workflow.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LangGraph orchestration for the multi-agent platform.

Graph structure:
  START → supervisor → [research | career | code_review] → evaluator → END

State flows through GraphState TypedDict.
The supervisor node uses JSON tool-calling to route to the correct agent.
"""

from __future__ import annotations

import json
import re
from typing import Annotated, Any, Dict, Optional

import structlog
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

from agents import (
    CareerAgent,
    CodeReviewAgent,
    EvaluationResult,
    EvaluatorAgent,
    ResearchAgent,
)
from agents.base import AgentOutput
from config import get_settings
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from prompts.prompt_registry import PromptRegistry

logger = structlog.get_logger()
settings = get_settings()
registry = PromptRegistry()


# ─────────────────────────────────────────────────────────────────────────────
# Graph State
# ─────────────────────────────────────────────────────────────────────────────

class GraphState(TypedDict):
    """
    Shared state flowing through every node in the graph.

    Fields
    ------
    user_input       : Original user message
    selected_agent   : Which agent was chosen by supervisor
    task_summary     : Reformulated task sent to the agent
    agent_params     : Optional overrides for agent parameters
    agent_output     : Output from the specialist agent
    evaluation       : Output from the evaluator
    final_report     : Assembled final response shown to user
    error            : Error message if anything failed
    """
    user_input: str
    selected_agent: str
    task_summary: str
    agent_params: Dict[str, Any]
    agent_output: Optional[AgentOutput]
    evaluation: Optional[EvaluationResult]
    final_report: str
    error: str


# ─────────────────────────────────────────────────────────────────────────────
# Node: Supervisor
# ─────────────────────────────────────────────────────────────────────────────

async def supervisor_node(state: GraphState) -> GraphState:
    """
    Routes the user request to the appropriate specialist agent.
    Uses the LLM to output structured JSON routing decision.
    """
    logger.info("supervisor_node.enter", user_input=state["user_input"][:80])

    llm = ChatGroq(
        api_key=settings.groq_api_key,
        model=settings.groq_model,
        temperature=0.0,  # Deterministic routing
        max_tokens=512,
    )

    system_prompt = registry.get("supervisor_agent").system_prompt

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=state["user_input"]),
    ]

    try:
        response = await llm.ainvoke(messages)
        raw = response.content.strip()

        # Strip markdown code fences if present
        raw = re.sub(r"```(?:json)?\s*", "", raw).strip().strip("`")

        routing = json.loads(raw)
        selected = routing.get("selected_agent", "research_agent")
        task_summary = routing.get("task_summary", state["user_input"])
        reasoning = routing.get("reasoning", "")

        logger.info(
            "supervisor_node.routed",
            agent=selected,
            reasoning=reasoning,
        )

        return {
            **state,
            "selected_agent": selected,
            "task_summary": task_summary,
        }

    except (json.JSONDecodeError, KeyError) as exc:
        logger.warning("supervisor_node.parse_error", error=str(exc))
        # Fallback: default to research agent
        return {
            **state,
            "selected_agent": "research_agent",
            "task_summary": state["user_input"],
        }


# ─────────────────────────────────────────────────────────────────────────────
# Node: Research Agent
# ─────────────────────────────────────────────────────────────────────────────

async def research_node(state: GraphState) -> GraphState:
    """Execute the Research Agent."""
    logger.info("research_node.enter")
    params = state.get("agent_params", {})

    agent = ResearchAgent(
        prompt_version=params.get("prompt_version"),
        search_depth=params.get("search_depth", "advanced"),
        max_results=params.get("max_results", 5),
        summary_length=params.get("summary_length", "standard"),
        temperature=params.get("temperature", 0.1),
    )

    output = await agent.run(
        task=state["task_summary"],
        **{k: v for k, v in params.items()
           if k in ("search_depth", "max_results", "summary_length")},
    )

    return {**state, "agent_output": output}


# ─────────────────────────────────────────────────────────────────────────────
# Node: Career Agent
# ─────────────────────────────────────────────────────────────────────────────

async def career_node(state: GraphState) -> GraphState:
    """Execute the Career Agent."""
    logger.info("career_node.enter")
    params = state.get("agent_params", {})

    agent = CareerAgent(
        prompt_version=params.get("prompt_version"),
        experience_level=params.get("experience_level", "student"),
        career_target=params.get("career_target", "AI Engineer"),
        industry_focus=params.get("industry_focus", "AI startups"),
        recommendation_depth=params.get("recommendation_depth", "standard"),
        temperature=params.get("temperature", 0.4),
    )

    output = await agent.run(task=state["task_summary"])

    return {**state, "agent_output": output}


# ─────────────────────────────────────────────────────────────────────────────
# Node: Code Review Agent
# ─────────────────────────────────────────────────────────────────────────────

async def code_review_node(state: GraphState) -> GraphState:
    """Execute the Code Review Agent."""
    logger.info("code_review_node.enter")
    params = state.get("agent_params", {})

    agent = CodeReviewAgent(
        prompt_version=params.get("prompt_version"),
        strictness_level=params.get("strictness_level", "standard"),
        security_focus=params.get("security_focus", True),
        performance_focus=params.get("performance_focus", True),
        explanation_detail=params.get("explanation_detail", "standard"),
        temperature=params.get("temperature", 0.1),
    )

    output = await agent.run(
        task=state["task_summary"],
        language=params.get("language"),
    )

    return {**state, "agent_output": output}


# ─────────────────────────────────────────────────────────────────────────────
# Node: Evaluator Agent
# ─────────────────────────────────────────────────────────────────────────────

async def evaluator_node(state: GraphState) -> GraphState:
    """Evaluate the specialist agent's output and build the final report."""
    logger.info("evaluator_node.enter")

    agent_output: AgentOutput = state["agent_output"]

    if not agent_output or not agent_output.success:
        error_msg = agent_output.error if agent_output else "No output produced"
        return {
            **state,
            "final_report": f"❌ Agent execution failed: {error_msg}",
            "error": error_msg,
        }

    evaluator = EvaluatorAgent()
    evaluation = await evaluator.evaluate(agent_output)

    # ── Assemble the final report ──────────────────────────────────────────
    status_emoji = {"PASS": "✅", "CONDITIONAL PASS": "⚠️", "FAIL": "❌"}.get(
        evaluation.certification_status, "❓"
    )

    final_report = (
        f"# Agentic AI Platform — Final Report\n\n"
        f"## Agent Response\n\n"
        f"{agent_output.result}\n\n"
        f"---\n\n"
        f"## Quality Evaluation\n\n"
        f"| Metric | Score |\n"
        f"|--------|-------|\n"
        f"| Accuracy | {evaluation.accuracy}/10 |\n"
        f"| Completeness | {evaluation.completeness}/10 |\n"
        f"| Relevance | {evaluation.relevance}/10 |\n"
        f"| Structure | {evaluation.structure}/10 |\n"
        f"| Tool Usage Quality | {evaluation.tool_usage_quality}/10 |\n"
        f"| Hallucination Risk | {evaluation.hallucination_risk} |\n\n"
        f"**Overall Score:** {evaluation.overall_score}/100\n\n"
        f"**Certification Status:** {status_emoji} {evaluation.certification_status}\n\n"
        f"**Agent:** {agent_output.agent_name} | "
        f"**Prompt:** {agent_output.prompt_version} | "
        f"**Latency:** {agent_output.latency_ms}ms\n"
    )

    logger.info(
        "evaluator_node.done",
        score=evaluation.overall_score,
        status=evaluation.certification_status,
    )

    return {
        **state,
        "evaluation": evaluation,
        "final_report": final_report,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Router: supervisor → specialist
# ─────────────────────────────────────────────────────────────────────────────

def route_to_agent(state: GraphState) -> str:
    """Conditional edge: supervisor → research | career | code_review."""
    agent = state.get("selected_agent", "research_agent")
    valid = {"research_agent", "career_agent", "code_review_agent"}
    if agent not in valid:
        logger.warning("route_to_agent.unknown", agent=agent)
        return "research_agent"
    return agent


# ─────────────────────────────────────────────────────────────────────────────
# Graph Builder
# ─────────────────────────────────────────────────────────────────────────────

def build_graph() -> StateGraph:
    """
    Construct and compile the LangGraph workflow.

    Returns a compiled CompiledGraph ready for .ainvoke() / .invoke().
    """
    builder = StateGraph(GraphState)

    # ── Add nodes ─────────────────────────────────────────────────────────
    builder.add_node("supervisor",    supervisor_node)
    builder.add_node("research_agent",    research_node)
    builder.add_node("career_agent",      career_node)
    builder.add_node("code_review_agent", code_review_node)
    builder.add_node("evaluator",     evaluator_node)

    # ── Entry point ───────────────────────────────────────────────────────
    builder.add_edge(START, "supervisor")

    # ── Conditional routing from supervisor ───────────────────────────────
    builder.add_conditional_edges(
        "supervisor",
        route_to_agent,
        {
            "research_agent":    "research_agent",
            "career_agent":      "career_agent",
            "code_review_agent": "code_review_agent",
        },
    )

    # ── All specialist agents feed into evaluator ─────────────────────────
    builder.add_edge("research_agent",    "evaluator")
    builder.add_edge("career_agent",      "evaluator")
    builder.add_edge("code_review_agent", "evaluator")

    # ── Evaluator → END ───────────────────────────────────────────────────
    builder.add_edge("evaluator", END)

    return builder.compile()


# Singleton compiled graph
_graph = None


def get_graph():
    """Return the singleton compiled graph (lazy initialisation)."""
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


async def run_workflow(
    user_input: str,
    agent_params: Optional[Dict[str, Any]] = None,
) -> GraphState:
    """
    High-level entry point: run the full multi-agent workflow.

    Parameters
    ----------
    user_input   : The raw user message.
    agent_params : Optional parameter overrides forwarded to the specialist agent.

    Returns
    -------
    The final GraphState containing agent_output, evaluation, and final_report.
    """
    graph = get_graph()

    initial_state: GraphState = {
        "user_input":     user_input,
        "selected_agent": "",
        "task_summary":   "",
        "agent_params":   agent_params or {},
        "agent_output":   None,
        "evaluation":     None,
        "final_report":   "",
        "error":          "",
    }

    logger.info("workflow.start", input=user_input[:80])
    result = await graph.ainvoke(initial_state)
    logger.info(
        "workflow.complete",
        agent=result.get("selected_agent"),
        score=result.get("evaluation").overall_score if result.get("evaluation") else None,
    )
    return result