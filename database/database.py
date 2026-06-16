"""
database.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Async SQLAlchemy database setup.
Stores:
  - AgentRun      : Every invocation with output and metadata
  - EvalRecord    : Evaluation scores linked to an AgentRun
  - PromptVersion : Audit log for active prompt versions
"""

from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, relationship, sessionmaker

from config import get_settings

settings = get_settings()

# ── Engine & Session ──────────────────────────────────────────────────────────
engine = create_async_engine(
    settings.database_url,
    echo=False,
    future=True,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
)

AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ── Base Model ────────────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    pass


# ── Tables ────────────────────────────────────────────────────────────────────

class AgentRun(Base):
    """One execution of a specialist agent."""
    __tablename__ = "agent_runs"

    id            = Column(Integer, primary_key=True, index=True)
    agent_name    = Column(String(64), nullable=False, index=True)
    version       = Column(String(16), nullable=False)
    prompt_version = Column(String(16), nullable=False)
    task          = Column(Text, nullable=False)
    result        = Column(Text, nullable=False)
    success       = Column(Boolean, default=True)
    error         = Column(Text, nullable=True)
    latency_ms    = Column(Float, default=0.0)
    metadata_json = Column(JSON, default={})
    created_at    = Column(DateTime, default=datetime.utcnow)

    # Relationship
    evaluation    = relationship("EvalRecord", back_populates="agent_run", uselist=False)


class EvalRecord(Base):
    """Evaluation scores for a single AgentRun."""
    __tablename__ = "eval_records"

    id                   = Column(Integer, primary_key=True, index=True)
    agent_run_id         = Column(Integer, ForeignKey("agent_runs.id"), nullable=False)
    accuracy             = Column(Float, default=0.0)
    completeness         = Column(Float, default=0.0)
    relevance            = Column(Float, default=0.0)
    structure            = Column(Float, default=0.0)
    tool_usage_quality   = Column(Float, default=0.0)
    hallucination_risk   = Column(String(16), default="Medium")
    overall_score        = Column(Float, default=0.0)
    certification_status = Column(String(32), default="FAIL")
    strengths            = Column(Text, default="")
    weaknesses           = Column(Text, default="")
    raw_report           = Column(Text, default="")
    latency_ms           = Column(Float, default=0.0)
    created_at           = Column(DateTime, default=datetime.utcnow)

    agent_run            = relationship("AgentRun", back_populates="evaluation")


class PromptAudit(Base):
    """Audit trail for prompt version changes."""
    __tablename__ = "prompt_audit"

    id          = Column(Integer, primary_key=True, index=True)
    agent_name  = Column(String(64), nullable=False)
    version     = Column(String(16), nullable=False)
    notes       = Column(Text, default="")
    activated_at = Column(DateTime, default=datetime.utcnow)


# ── DB Lifecycle ──────────────────────────────────────────────────────────────

async def init_db() -> None:
    """Create all tables if they don't exist."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncSession:
    """FastAPI dependency: yields an async DB session."""
    async with AsyncSessionLocal() as session:
        yield session


# ── Repository helpers ────────────────────────────────────────────────────────

async def save_run(session: AsyncSession, output) -> AgentRun:
    """Persist an AgentOutput to the database."""
    run = AgentRun(
        agent_name=output.agent_name,
        version=output.version,
        prompt_version=output.prompt_version,
        task=output.task[:1000],
        result=output.result[:10_000],
        success=output.success,
        error=output.error,
        latency_ms=output.latency_ms,
        metadata_json=output.metadata,
    )
    session.add(run)
    await session.commit()
    await session.refresh(run)
    return run


async def save_eval(session: AsyncSession, run_id: int, eval_result) -> EvalRecord:
    """Persist an EvaluationResult to the database."""
    rec = EvalRecord(
        agent_run_id=run_id,
        accuracy=eval_result.accuracy,
        completeness=eval_result.completeness,
        relevance=eval_result.relevance,
        structure=eval_result.structure,
        tool_usage_quality=eval_result.tool_usage_quality,
        hallucination_risk=eval_result.hallucination_risk,
        overall_score=eval_result.overall_score,
        certification_status=eval_result.certification_status,
        strengths=eval_result.strengths,
        weaknesses=eval_result.weaknesses,
        raw_report=eval_result.raw_report[:10_000],
        latency_ms=eval_result.latency_ms,
    )
    session.add(rec)
    await session.commit()
    await session.refresh(rec)
    return rec