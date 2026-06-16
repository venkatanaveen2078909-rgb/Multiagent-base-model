# `api/app.py` — Line-by-Line Explanation

**File:** `api/app.py`  
**Role:** The FastAPI application that exposes the platform's capabilities via REST endpoints. It wires together the agents, the database, and the LangGraph workflow.

---

## App Initialization (Lines 49–72)

```python
app = FastAPI(
    title="Agentic AI Platform",
    description="...",
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
```

- **`FastAPI(...)`**: Instantiates the ASGI web application with OpenAPI documentation metadata.
- **`CORSMiddleware`**: Adds Cross-Origin Resource Sharing headers so a web frontend running on a different port can call this API.
- **`@app.on_event("startup")`**: Registers a hook to run when the server boots. `init_db()` connects to SQLite and creates the tables (if they don't exist yet).

---

## Request/Response Schemas (Lines 76–132)

```python
class WorkflowRequest(BaseModel):
    user_input: str = Field(..., min_length=3, description="User's natural language request")
    agent_params: Dict[str, Any] = Field(default_factory=dict, description="Optional agent parameter overrides")

class ResearchRequest(BaseModel):
    task: str = Field(..., description="Research question or topic")
    # ... other fields ...
```

- **`BaseModel`**: Inherits from Pydantic. These classes validate incoming JSON requests and generate the Swagger documentation.
- **`Field(...)`**: Provides extra validation (like `min_length=3`, bounds like `ge=1, le=10`) and descriptions for the auto-generated API docs. If a user sends a temperature of `1.5`, Pydantic will auto-reject it with a 422 HTTP error.

---

## Persistence Utility (Lines 136–163)

```python
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
```

- A DRY (Don't Repeat Yourself) helper function. Because almost every endpoint does "run agent -> evaluate -> save to DB", this encapsulates the DB save operations using functions imported from `database.py`.

---

## Endpoint: Health Check (Lines 168–175)

```python
@app.get("/health")
async def health():
    return {
        "status": "ok",
        "version": "1.0.0",
        "groq_configured": settings.has_groq_key,
        "tavily_configured": settings.has_tavily_key,
    }
```

- Basic liveness probe. Helpful for Docker/Kubernetes health checks and for frontends to verify API availability and API key configuration status.

---

## Endpoint: Full Workflow (Lines 179–210)

```python
@app.post("/run", response_model=Dict[str, Any], summary="Run the full multi-agent workflow")
async def run_full_workflow(
    req: WorkflowRequest,
    session: AsyncSession = Depends(get_session),
):
    """Entry point for the full pipeline: Supervisor → Specialist Agent → Evaluator"""
    try:
        state = await run_workflow(req.user_input, req.agent_params)
```

- **`Depends(get_session)`**: FastAPI Dependency Injection. It automatically manages the lifecycle of the database session, opening it before the request and closing it after.
- Calls `run_workflow` (the LangGraph execution) and gets the final state dictionary back.

```python
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
```

- Extracts the `output` and `evaluation` from the graph state, saves them to SQLite.
- Returns a structured dictionary containing the IDs, the routing decisions, and the final combined markdown report.
- Catches errors and raises them as `HTTPException(500)` so the client gets a clean JSON error response rather than dropping the connection.

---

## Direct Agent Endpoints (Lines 214–305)

```python
@app.post("/agents/research", summary="Run Research Agent directly")
async def run_research(
    req: ResearchRequest,
    session: AsyncSession = Depends(get_session),
):
    agent = ResearchAgent(
        prompt_version=req.prompt_version,
        search_depth=req.search_depth,
        # ...
    )
    output = await agent.run(req.task)

    evaluator = EvaluatorAgent()
    evaluation = await evaluator.evaluate(output)

    run, _ = await _persist_run_and_eval(session, output, evaluation)
    
    return AgentRunResponse(...)
```

- Bypasses the Supervisor agent. The user explicitly requests the Research (or Career/Code Review) agent.
- Explicitly instantiates the specialist agent using parameters from the Pydantic request.
- Manually runs the `EvaluatorAgent` over the result to maintain the platform's quality-assurance guarantee.
- (Similar structure applies for `/agents/career` and `/agents/code-review` endpoints).

---

## Endpoints: History and Prompts (Lines 327–407)

```python
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
    # ... formats and returns ...
```

- Uses SQLAlchemy 2.0 async query syntax (`select()`, `where()`) to fetch history.
- **`/prompts` and `/prompts/compare`**: Simple wrappers around the `PromptRegistry` utility to allow frontends to list versions and compare them for debugging.
