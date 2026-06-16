"""Quick integration test for API + UI assets."""
import sys
import httpx

BASE = "http://127.0.0.1:8001"
client = httpx.Client(timeout=120.0)
results = []


def check(name, fn):
    try:
        fn()
        results.append((name, True, ""))
        print(f"PASS: {name}")
    except Exception as e:
        results.append((name, False, str(e)))
        print(f"FAIL: {name} -> {e}")


# Static UI
check("GET /", lambda: client.get(f"{BASE}/").raise_for_status())
check("GET /assets/css/app.css", lambda: client.get(f"{BASE}/assets/css/app.css").raise_for_status())
check("GET /assets/js/app.js", lambda: client.get(f"{BASE}/assets/js/app.js").raise_for_status())

html = client.get(f"{BASE}/").text
check("UI has sidebar", lambda: "sidebar" in html or (_ for _ in ()).throw(Exception("no sidebar")))
check("UI has app.js", lambda: "app.js" in html or (_ for _ in ()).throw(Exception("no app.js")))

# Health
h = client.get(f"{BASE}/health").json()
check("GET /health", lambda: h["status"] == "ok" or (_ for _ in ()).throw(Exception(str(h))))
print(f"  groq={h.get('groq_configured')} tavily={h.get('tavily_configured')}")

# Prompts
p = client.get(f"{BASE}/prompts").json()
check("GET /prompts", lambda: len(p) >= 5 or (_ for _ in ()).throw(Exception("missing agents")))

cmp = client.post(
    f"{BASE}/prompts/compare",
    json={"agent": "research_agent", "version_a": "v1", "version_b": "v2"},
).json()
check("POST /prompts/compare", lambda: "prompt" in cmp["version_a"])

# Runs
runs = client.get(f"{BASE}/runs?limit=5").json()
check("GET /runs", lambda: isinstance(runs, list))

# Evaluator
ev = client.post(
    f"{BASE}/evaluate",
    json={
        "agent_output_text": "## Summary\nPython is a programming language.\n## Key Findings\n- High level\n## Sources\n1. python.org",
        "agent_name": "research_agent",
        "task": "What is Python?",
    },
).json()
check("POST /evaluate", lambda: 0 <= ev["overall_score"] <= 100)

# Career
cr = client.post(
    f"{BASE}/agents/career",
    json={
        "task": "I am a CS student interested in AI.",
        "experience_level": "student",
        "career_target": "AI Engineer",
    },
).json()
check("POST /agents/career", lambda: cr.get("success") and len(cr.get("result", "")) > 50)

# Code review
cv = client.post(
    f"{BASE}/agents/code-review",
    json={"code": "def add(x, items=[]):\n    items.append(x)\n    return items"},
).json()
check("POST /agents/code-review", lambda: cv.get("success") and len(cv.get("result", "")) > 30)

# Run detail
if cr.get("run_id"):
    rid = cr["run_id"]
    detail = client.get(f"{BASE}/runs/{rid}").json()
    check("GET /runs/{id}", lambda: detail["id"] == rid and detail.get("evaluation"))
    check("Run detail has strengths", lambda: "strengths" in (detail.get("evaluation") or {}))

# Research (slower, needs Tavily)
if h.get("tavily_configured"):
    rs = client.post(
        f"{BASE}/agents/research",
        json={"task": "What is LangGraph?", "search_depth": "basic", "max_results": 2},
    ).json()
    check("POST /agents/research", lambda: rs.get("success") and len(rs.get("result", "")) > 50)
else:
    print("SKIP: research (no tavily key)")

# Full workflow
wf = client.post(f"{BASE}/run", json={"user_input": "Review this code: def foo(): pass"}).json()
check("POST /run", lambda: wf.get("selected_agent") and wf.get("final_report"))

failed = [r for r in results if not r[1]]
print(f"\n=== {len(results) - len(failed)}/{len(results)} passed ===")
for name, ok, err in failed:
    print(f"  FAILED: {name}: {err}")
sys.exit(1 if failed else 0)
