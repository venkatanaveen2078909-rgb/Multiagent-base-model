"""
api/app.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FastAPI application exposing all agent capabilities via REST.

Endpoints
─────────
POST /run                  — Full workflow (supervisor → agent → evaluator)
POST /agents/research      — Research agent directly
POST /agents/career        — Career agent directly
POST /agents/code-review   — Code review agent directly
POST /evaluate             — Evaluate any text output
GET  /runs                 — List recent agent runs
GET  /runs/{id}            — Get single run with evaluation
GET  /prompts              — List all prompt versions
POST /prompts/compare      — Compare two prompt versions
GET  /health               — Health check
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from agents import (
    CareerAgent,
    CodeReviewAgent,
    EvaluationResult,
    EvaluatorAgent,
    ResearchAgent,
)
from agents.base import AgentOutput
from config import get_settings
from database import AgentRun, EvalRecord, get_session, init_db, save_eval, save_run
from graph.workflow import run_workflow
from prompts.prompt_registry import PromptRegistry

logger = structlog.get_logger()
settings = get_settings()
registry = PromptRegistry()

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Agentic AI Platform",
    description=(
        "Multi-agent system with Research, Career, Code Review, "
        "Evaluator, and Supervisor agents. Built with LangGraph + Groq."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    await init_db()
    logger.info("api.startup", status="ready")


# ── Request / Response Schemas ────────────────────────────────────────────────

class WorkflowRequest(BaseModel):
    user_input: str = Field(..., min_length=3, description="User's natural language request")
    agent_params: Dict[str, Any] = Field(default_factory=dict, description="Optional agent parameter overrides")


class ResearchRequest(BaseModel):
    task: str = Field(..., description="Research question or topic")
    prompt_version: Optional[str] = None
    search_depth: str = "advanced"
    max_results: int = Field(5, ge=1, le=10)
    summary_length: str = "standard"
    temperature: float = Field(0.1, ge=0.0, le=1.0)


class CareerRequest(BaseModel):
    task: str = Field(..., description="Resume text or career question")
    prompt_version: Optional[str] = None
    experience_level: str = "student"
    career_target: str = "AI Engineer"
    industry_focus: str = "AI startups"
    recommendation_depth: str = "standard"
    temperature: float = Field(0.4, ge=0.0, le=1.0)


class CodeReviewRequest(BaseModel):
    code: str = Field(..., description="Code to review")
    prompt_version: Optional[str] = None
    strictness_level: str = "standard"
    security_focus: bool = True
    performance_focus: bool = True
    explanation_detail: str = "standard"
    language: Optional[str] = None
    temperature: float = Field(0.1, ge=0.0, le=1.0)


class EvaluateRequest(BaseModel):
    agent_output_text: str = Field(..., description="The agent output text to evaluate")
    agent_name: str = "unknown_agent"
    prompt_version: str = "v1"
    task: str = "Not specified"


class AgentRunResponse(BaseModel):
    run_id: int
    agent_name: str
    prompt_version: str
    result: str
    success: bool
    latency_ms: float
    evaluation: Optional[Dict[str, Any]] = None


class PromptCompareRequest(BaseModel):
    agent: str
    version_a: str
    version_b: str


# ── Utility ───────────────────────────────────────────────────────────────────

async def _persist_run_and_eval(
    session: AsyncSession,
    output: AgentOutput,
    evaluation: Optional[EvaluationResult] = None,
) -> tuple:
    run = await save_run(session, output)
    eval_rec = None
    if evaluation:
        eval_rec = await save_eval(session, run.id, evaluation)
    return run, eval_rec


def _eval_to_dict(e: Optional[EvaluationResult]) -> Optional[Dict]:
    if not e:
        return None
    return {
        "accuracy": e.accuracy,
        "completeness": e.completeness,
        "relevance": e.relevance,
        "structure": e.structure,
        "tool_usage_quality": e.tool_usage_quality,
        "hallucination_risk": e.hallucination_risk,
        "overall_score": e.overall_score,
        "certification_status": e.certification_status,
        "strengths": e.strengths,
        "weaknesses": e.weaknesses,
    }


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "version": "1.0.0",
        "groq_configured": settings.has_groq_key,
        "tavily_configured": settings.has_tavily_key,
    }


# ── Full Workflow ──────────────────────────────────────────────────────────────

@app.post("/run", response_model=Dict[str, Any], summary="Run the full multi-agent workflow")
async def run_full_workflow(
    req: WorkflowRequest,
    session: AsyncSession = Depends(get_session),
):
    """
    Entry point for the full pipeline:
    Supervisor → Specialist Agent → Evaluator

    Returns the agent's output, evaluation scores, and final report.
    """
    try:
        state = await run_workflow(req.user_input, req.agent_params)

        output = state.get("agent_output")
        evaluation = state.get("evaluation")

        run, _ = await _persist_run_and_eval(session, output, evaluation)

        return {
            "run_id": run.id,
            "selected_agent": state.get("selected_agent"),
            "task_summary": state.get("task_summary"),
            "result": output.result if output else "",
            "final_report": state.get("final_report"),
            "evaluation": _eval_to_dict(evaluation),
            "latency_ms": output.latency_ms if output else 0,
        }
    except Exception as exc:
        logger.error("api.run_workflow.error", error=str(exc))
        raise HTTPException(status_code=500, detail=str(exc))


# ── Direct Agent Endpoints ────────────────────────────────────────────────────

@app.post("/agents/research", summary="Run Research Agent directly")
async def run_research(
    req: ResearchRequest,
    session: AsyncSession = Depends(get_session),
):
    agent = ResearchAgent(
        prompt_version=req.prompt_version,
        search_depth=req.search_depth,
        max_results=req.max_results,
        summary_length=req.summary_length,
        temperature=req.temperature,
    )
    output = await agent.run(req.task)

    # Auto-evaluate
    evaluator = EvaluatorAgent()
    evaluation = await evaluator.evaluate(output)

    run, _ = await _persist_run_and_eval(session, output, evaluation)

    return AgentRunResponse(
        run_id=run.id,
        agent_name=output.agent_name,
        prompt_version=output.prompt_version,
        result=output.result,
        success=output.success,
        latency_ms=output.latency_ms,
        evaluation=_eval_to_dict(evaluation),
    )


@app.post("/agents/career", summary="Run Career Agent directly")
async def run_career(
    req: CareerRequest,
    session: AsyncSession = Depends(get_session),
):
    agent = CareerAgent(
        prompt_version=req.prompt_version,
        experience_level=req.experience_level,
        career_target=req.career_target,
        industry_focus=req.industry_focus,
        recommendation_depth=req.recommendation_depth,
        temperature=req.temperature,
    )
    output = await agent.run(req.task)

    evaluator = EvaluatorAgent()
    evaluation = await evaluator.evaluate(output)

    run, _ = await _persist_run_and_eval(session, output, evaluation)

    return AgentRunResponse(
        run_id=run.id,
        agent_name=output.agent_name,
        prompt_version=output.prompt_version,
        result=output.result,
        success=output.success,
        latency_ms=output.latency_ms,
        evaluation=_eval_to_dict(evaluation),
    )


@app.post("/agents/code-review", summary="Run Code Review Agent directly")
async def run_code_review(
    req: CodeReviewRequest,
    session: AsyncSession = Depends(get_session),
):
    agent = CodeReviewAgent(
        prompt_version=req.prompt_version,
        strictness_level=req.strictness_level,
        security_focus=req.security_focus,
        performance_focus=req.performance_focus,
        explanation_detail=req.explanation_detail,
        temperature=req.temperature,
    )
    output = await agent.run(req.code, language=req.language)

    evaluator = EvaluatorAgent()
    evaluation = await evaluator.evaluate(output)

    run, _ = await _persist_run_and_eval(session, output, evaluation)

    return AgentRunResponse(
        run_id=run.id,
        agent_name=output.agent_name,
        prompt_version=output.prompt_version,
        result=output.result,
        success=output.success,
        latency_ms=output.latency_ms,
        evaluation=_eval_to_dict(evaluation),
    )


@app.post("/evaluate", summary="Evaluate any agent output text")
async def evaluate_output(req: EvaluateRequest):
    """Evaluate arbitrary text as if it were agent output."""
    from agents.base import AgentOutput as AO

    synthetic_output = AO(
        agent_name=req.agent_name,
        version="manual",
        prompt_version=req.prompt_version,
        task=req.task,
        result=req.agent_output_text,
    )
    evaluator = EvaluatorAgent()
    evaluation = await evaluator.evaluate(synthetic_output)
    return _eval_to_dict(evaluation)


# ── Run History ───────────────────────────────────────────────────────────────

@app.get("/runs", summary="List recent agent runs")
async def list_runs(
    limit: int = Query(20, ge=1, le=100),
    agent_name: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
):
    q = select(AgentRun).order_by(desc(AgentRun.created_at)).limit(limit)
    if agent_name:
        q = q.where(AgentRun.agent_name == agent_name)
    result = await session.execute(q)
    runs = result.scalars().all()
    return [
        {
            "id": r.id,
            "agent_name": r.agent_name,
            "prompt_version": r.prompt_version,
            "task": r.task[:100],
            "success": r.success,
            "latency_ms": r.latency_ms,
            "created_at": r.created_at.isoformat(),
        }
        for r in runs
    ]


@app.get("/runs/{run_id}", summary="Get a single run with evaluation")
async def get_run(run_id: int, session: AsyncSession = Depends(get_session)):
    run = await session.get(AgentRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    eval_q = select(EvalRecord).where(EvalRecord.agent_run_id == run_id)
    eval_result = await session.execute(eval_q)
    ev = eval_result.scalar_one_or_none()

    return {
        "id": run.id,
        "agent_name": run.agent_name,
        "prompt_version": run.prompt_version,
        "task": run.task,
        "result": run.result,
        "success": run.success,
        "latency_ms": run.latency_ms,
        "metadata": run.metadata_json,
        "created_at": run.created_at.isoformat(),
        "evaluation": {
            "accuracy": ev.accuracy,
            "completeness": ev.completeness,
            "relevance": ev.relevance,
            "structure": ev.structure,
            "tool_usage_quality": ev.tool_usage_quality,
            "hallucination_risk": ev.hallucination_risk,
            "overall_score": ev.overall_score,
            "certification_status": ev.certification_status,
            "strengths": ev.strengths,
            "weaknesses": ev.weaknesses,
        } if ev else None,
    }


# ── Prompt Registry ───────────────────────────────────────────────────────────

@app.get("/prompts", summary="List all agents and their prompt versions")
async def list_prompts():
    result = {}
    for agent in registry.all_agents():
        versions = registry.list_versions(agent)
        result[agent] = [
            {
                "version": v,
                "notes": registry.get(agent, v).notes,
                "created_at": registry.get(agent, v).created_at,
            }
            for v in versions
        ]
    return result


@app.post("/prompts/compare", summary="Compare two prompt versions side-by-side")
async def compare_prompts(req: PromptCompareRequest):
    try:
        return registry.compare(req.agent, req.version_a, req.version_b)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ── Web UI ────────────────────────────────────────────────────────────────────

@app.get("/", include_in_schema=False)
async def serve_ui():
    index = STATIC_DIR / "index.html"
    if not index.exists():
        raise HTTPException(status_code=404, detail="UI not found. Run from project root.")
    return FileResponse(index)


if STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(STATIC_DIR)), name="assets")