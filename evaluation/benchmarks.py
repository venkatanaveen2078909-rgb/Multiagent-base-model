"""
evaluation/benchmarks.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DeepEval benchmark suites for all agents.

Each agent has 20 test cases covering diverse scenarios.
Run with:  pytest evaluation/benchmarks.py -v
Or:        python evaluation/benchmarks.py
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import List

# DeepEval imports
try:
    from deepeval import evaluate
    from deepeval.metrics import (
        AnswerRelevancyMetric,
        FaithfulnessMetric,
        HallucinationMetric,
        GEval,
    )
    from deepeval.test_case import LLMTestCase
    DEEPEVAL_AVAILABLE = True
except ImportError:
    DEEPEVAL_AVAILABLE = False
    import warnings
    warnings.warn("deepeval not installed. Using lightweight fallback evaluation.")


@dataclass
class BenchmarkCase:
    """A single benchmark test case."""
    agent: str
    input: str
    expected_output_keywords: List[str]  # Keywords that must appear in a good response
    context: str = ""
    category: str = "general"


# ─────────────────────────────────────────────────────────────────────────────
# RESEARCH AGENT — 20 Test Cases
# ─────────────────────────────────────────────────────────────────────────────
RESEARCH_BENCHMARKS: List[BenchmarkCase] = [
    BenchmarkCase("research_agent", "What is LangGraph and how does it work?",
                  ["LangGraph", "graph", "nodes", "state"], category="AI/ML"),
    BenchmarkCase("research_agent", "Latest trends in large language models 2024",
                  ["transformer", "attention", "fine-tuning", "context window"], category="AI/ML"),
    BenchmarkCase("research_agent", "What is retrieval-augmented generation (RAG)?",
                  ["retrieval", "vector", "embedding", "context"], category="AI/ML"),
    BenchmarkCase("research_agent", "Explain the difference between SQL and NoSQL databases",
                  ["SQL", "NoSQL", "relational", "schema", "scalability"], category="databases"),
    BenchmarkCase("research_agent", "What are the best Python frameworks for building REST APIs?",
                  ["FastAPI", "Django", "Flask", "performance"], category="backend"),
    BenchmarkCase("research_agent", "How does Kubernetes work?",
                  ["container", "orchestration", "pod", "cluster"], category="devops"),
    BenchmarkCase("research_agent", "What is quantum computing and its current state?",
                  ["qubit", "superposition", "entanglement", "gate"], category="quantum"),
    BenchmarkCase("research_agent", "Best practices for securing a FastAPI application",
                  ["JWT", "OAuth", "HTTPS", "validation"], category="security"),
    BenchmarkCase("research_agent", "What is vector search and when should you use it?",
                  ["embedding", "similarity", "FAISS", "Pinecone"], category="AI/ML"),
    BenchmarkCase("research_agent", "Explain Redis architecture and use cases",
                  ["cache", "pub/sub", "in-memory", "persistence"], category="databases"),
    BenchmarkCase("research_agent", "What are the top AI startups to watch in 2024?",
                  ["startup", "AI", "funding", "model"], category="industry"),
    BenchmarkCase("research_agent", "How does transformer architecture work?",
                  ["attention", "encoder", "decoder", "token"], category="AI/ML"),
    BenchmarkCase("research_agent", "What is the CAP theorem in distributed systems?",
                  ["consistency", "availability", "partition", "trade-off"], category="distributed"),
    BenchmarkCase("research_agent", "Latest developments in agentic AI systems",
                  ["agent", "tool", "planning", "memory"], category="AI/ML"),
    BenchmarkCase("research_agent", "What is GraphQL and how does it differ from REST?",
                  ["query", "schema", "mutation", "REST"], category="backend"),
    BenchmarkCase("research_agent", "How does Docker containerisation work?",
                  ["container", "image", "Dockerfile", "layer"], category="devops"),
    BenchmarkCase("research_agent", "What is the current state of quantum machine learning?",
                  ["quantum", "circuit", "hybrid", "NISQ"], category="quantum"),
    BenchmarkCase("research_agent", "Best practices for async programming in Python",
                  ["asyncio", "await", "coroutine", "event loop"], category="python"),
    BenchmarkCase("research_agent", "What are the OWASP Top 10 security risks?",
                  ["injection", "authentication", "XSS", "vulnerability"], category="security"),
    BenchmarkCase("research_agent", "How does Celery work with Redis for task queuing?",
                  ["task", "worker", "broker", "queue"], category="backend"),
]

# ─────────────────────────────────────────────────────────────────────────────
# CAREER AGENT — 20 Test Cases
# ─────────────────────────────────────────────────────────────────────────────
CAREER_BENCHMARKS: List[BenchmarkCase] = [
    BenchmarkCase("career_agent",
                  "I'm a 3rd year CS student with Python, ML basics, and one FastAPI project. I want to become an AI Engineer.",
                  ["roadmap", "skill gap", "project", "internship"], category="student"),
    BenchmarkCase("career_agent",
                  "I know React and Node.js. How do I transition to backend engineering?",
                  ["backend", "system design", "database", "API"], category="transition"),
    BenchmarkCase("career_agent",
                  "What skills do I need to get hired at a top AI startup in India?",
                  ["LLM", "Python", "system design", "portfolio"], category="industry"),
    BenchmarkCase("career_agent",
                  "I have 2 years of data science experience. How do I move to ML Engineering?",
                  ["MLOps", "deployment", "infrastructure", "pipeline"], category="transition"),
    BenchmarkCase("career_agent",
                  "What's the difference between a Data Scientist, ML Engineer, and AI Engineer?",
                  ["data scientist", "ML engineer", "deployment", "research"], category="roles"),
    BenchmarkCase("career_agent",
                  "I want to build projects for my resume to get into AI. What should I build?",
                  ["project", "portfolio", "GitHub", "LLM"], category="student"),
    BenchmarkCase("career_agent",
                  "How should I prepare for a backend engineering interview at a product company?",
                  ["DSA", "system design", "API", "database"], category="interview"),
    BenchmarkCase("career_agent",
                  "What certifications are most valuable for an AI career in 2024?",
                  ["certification", "AWS", "TensorFlow", "cloud"], category="certifications"),
    BenchmarkCase("career_agent",
                  "I want to work at Google or OpenAI. What's the path from a tier-2 college in India?",
                  ["FAANG", "competitive programming", "research", "internship"], category="FAANG"),
    BenchmarkCase("career_agent",
                  "What open source contributions should an aspiring ML engineer make?",
                  ["open source", "contribution", "GitHub", "community"], category="student"),
    BenchmarkCase("career_agent",
                  "How do I negotiate salary as a fresh graduate at an AI startup?",
                  ["salary", "negotiation", "offer", "equity"], category="career"),
    BenchmarkCase("career_agent",
                  "I know LangChain and FastAPI. Should I go deeper or learn new frameworks?",
                  ["depth", "breadth", "specialisation", "stack"], category="career"),
    BenchmarkCase("career_agent",
                  "What is the career path for an AI Security Engineer?",
                  ["security", "AI", "red team", "certification"], category="hybrid"),
    BenchmarkCase("career_agent",
                  "How do I build a personal brand on LinkedIn as a CS student?",
                  ["LinkedIn", "content", "networking", "projects"], category="branding"),
    BenchmarkCase("career_agent",
                  "What are the best platforms to find AI engineering internships in India?",
                  ["internship", "platform", "Internshala", "LinkedIn"], category="internships"),
    BenchmarkCase("career_agent",
                  "How do I transition from a service-based company to a product company?",
                  ["product", "service", "skills", "portfolio"], category="transition"),
    BenchmarkCase("career_agent",
                  "What should a 6-month learning plan for becoming a backend engineer look like?",
                  ["month", "plan", "skill", "project"], category="roadmap"),
    BenchmarkCase("career_agent",
                  "Is pursuing research vs industry the better path for an AI career?",
                  ["research", "industry", "PhD", "startup"], category="career"),
    BenchmarkCase("career_agent",
                  "How do I stand out in a hackathon to get noticed by recruiters?",
                  ["hackathon", "project", "demo", "recruiter"], category="student"),
    BenchmarkCase("career_agent",
                  "What DSA topics are most important for product company interviews?",
                  ["arrays", "graphs", "dynamic programming", "complexity"], category="interview"),
]

# ─────────────────────────────────────────────────────────────────────────────
# CODE REVIEW AGENT — 20 Test Cases
# ─────────────────────────────────────────────────────────────────────────────
_CODE_SAMPLES = {
    "sql_injection": """
def get_user(username):
    query = f"SELECT * FROM users WHERE name = '{username}'"
    return db.execute(query)
""",
    "n_plus_one": """
def get_all_posts_with_authors():
    posts = Post.query.all()
    result = []
    for post in posts:
        author = User.query.get(post.author_id)
        result.append({'post': post, 'author': author})
    return result
""",
    "no_error_handling": """
import requests

def fetch_data(url):
    response = requests.get(url)
    return response.json()['data']
""",
    "mutable_default": """
def add_item(item, items=[]):
    items.append(item)
    return items
""",
    "global_state": """
counter = 0

def increment():
    global counter
    counter += 1
    return counter
""",
    "async_in_sync": """
import asyncio

def process():
    loop = asyncio.get_event_loop()
    result = loop.run_until_complete(some_async_func())
    return result
""",
    "hardcoded_secret": """
import psycopg2

def connect():
    conn = psycopg2.connect(
        host="localhost",
        database="mydb",
        user="admin",
        password="super_secret_password_123"
    )
    return conn
""",
    "inefficient_sort": """
def find_top_k(lst, k):
    sorted_list = sorted(lst, reverse=True)
    return sorted_list[:k]
""",
    "recursive_no_memo": """
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
""",
    "bare_except": """
def parse_config(path):
    try:
        with open(path) as f:
            return json.load(f)
    except:
        return {}
""",
}

REVIEW_CODE_TASKS = list(_CODE_SAMPLES.values())

CODE_REVIEW_BENCHMARKS: List[BenchmarkCase] = [
    BenchmarkCase("code_review_agent", _CODE_SAMPLES["sql_injection"],
                  ["SQL injection", "parameterised", "security", "vulnerability"], category="security"),
    BenchmarkCase("code_review_agent", _CODE_SAMPLES["n_plus_one"],
                  ["N+1", "query", "eager loading", "performance"], category="performance"),
    BenchmarkCase("code_review_agent", _CODE_SAMPLES["no_error_handling"],
                  ["exception", "error handling", "timeout", "try/except"], category="robustness"),
    BenchmarkCase("code_review_agent", _CODE_SAMPLES["mutable_default"],
                  ["mutable default", "None", "anti-pattern"], category="python"),
    BenchmarkCase("code_review_agent", _CODE_SAMPLES["global_state"],
                  ["global", "thread safety", "race condition"], category="concurrency"),
    BenchmarkCase("code_review_agent", _CODE_SAMPLES["async_in_sync"],
                  ["asyncio", "event loop", "async/await"], category="async"),
    BenchmarkCase("code_review_agent", _CODE_SAMPLES["hardcoded_secret"],
                  ["hardcoded", "environment variable", "secret", "security"], category="security"),
    BenchmarkCase("code_review_agent", _CODE_SAMPLES["inefficient_sort"],
                  ["O(n log n)", "heap", "partition", "performance"], category="performance"),
    BenchmarkCase("code_review_agent", _CODE_SAMPLES["recursive_no_memo"],
                  ["memoisation", "exponential", "dynamic programming", "cache"], category="performance"),
    BenchmarkCase("code_review_agent", _CODE_SAMPLES["bare_except"],
                  ["bare except", "specific exception", "logging"], category="error handling"),
    # 10 more varied cases
    BenchmarkCase("code_review_agent",
                  "def divide(a, b):\n    return a / b",
                  ["division by zero", "ZeroDivisionError", "edge case"], category="robustness"),
    BenchmarkCase("code_review_agent",
                  "password = input('Enter password: ')\nprint(f'Your password is {password}')",
                  ["password", "logging", "sensitive data"], category="security"),
    BenchmarkCase("code_review_agent",
                  "data = [x for x in range(10**8)]",
                  ["memory", "generator", "performance"], category="performance"),
    BenchmarkCase("code_review_agent",
                  "import pickle\nobj = pickle.loads(user_input)",
                  ["pickle", "deserialization", "arbitrary code execution"], category="security"),
    BenchmarkCase("code_review_agent",
                  "class Singleton:\n    _instance = None\n    def __new__(cls):\n        if cls._instance is None:\n            cls._instance = super().__new__(cls)\n        return cls._instance",
                  ["singleton", "thread safety", "lock"], category="patterns"),
    BenchmarkCase("code_review_agent",
                  "def process(items):\n    result = ''\n    for item in items:\n        result += str(item)\n    return result",
                  ["string concatenation", "O(n²)", "join"], category="performance"),
    BenchmarkCase("code_review_agent",
                  "import os\nos.system(f'echo {user_input}')",
                  ["command injection", "subprocess", "shell=False"], category="security"),
    BenchmarkCase("code_review_agent",
                  "def is_prime(n):\n    for i in range(2, n):\n        if n % i == 0:\n            return False\n    return True",
                  ["sqrt", "O(√n)", "optimisation"], category="performance"),
    BenchmarkCase("code_review_agent",
                  "async def handler():\n    time.sleep(5)\n    return 'done'",
                  ["blocking", "asyncio.sleep", "event loop"], category="async"),
    BenchmarkCase("code_review_agent",
                  "def get_data():\n    conn = sqlite3.connect('db.sqlite')\n    cursor = conn.cursor()\n    cursor.execute('SELECT * FROM users')\n    return cursor.fetchall()",
                  ["connection pool", "context manager", "close"], category="database"),
]

# ─────────────────────────────────────────────────────────────────────────────
# EVALUATOR AGENT — 20 Test Cases (testing the evaluator itself)
# ─────────────────────────────────────────────────────────────────────────────
EVALUATOR_BENCHMARKS: List[BenchmarkCase] = [
    BenchmarkCase("evaluator_agent",
                  "A perfect research report with citations, key findings, and insights.",
                  ["Accuracy", "Completeness", "score", "PASS"], category="research_eval"),
    BenchmarkCase("evaluator_agent",
                  "A research report with no sources and speculative claims.",
                  ["hallucination", "sources", "score", "risk"], category="research_eval"),
    BenchmarkCase("evaluator_agent",
                  "A career roadmap missing specific project recommendations.",
                  ["Completeness", "gap", "recommendation"], category="career_eval"),
    BenchmarkCase("evaluator_agent",
                  "A code review that found the SQL injection but missed buffer overflow.",
                  ["Completeness", "missed", "security"], category="code_eval"),
    BenchmarkCase("evaluator_agent",
                  "An agent output that confidently states wrong facts about Python version history.",
                  ["accuracy", "factual error", "hallucination", "FAIL"], category="accuracy_eval"),
    BenchmarkCase("evaluator_agent",
                  "A perfectly structured report with all required sections.",
                  ["structure", "format", "score"], category="structure_eval"),
    BenchmarkCase("evaluator_agent",
                  "An output that answered a different question than asked.",
                  ["relevance", "off-topic", "score"], category="relevance_eval"),
    BenchmarkCase("evaluator_agent",
                  "A career agent output with excellent roadmap but no internship suggestions.",
                  ["Completeness", "internship", "missing"], category="career_eval"),
    BenchmarkCase("evaluator_agent",
                  "A code review that used no tools and provided general advice only.",
                  ["tool usage", "specific", "quality"], category="tool_eval"),
    BenchmarkCase("evaluator_agent",
                  "A research report that cites 10 different authoritative sources.",
                  ["sources", "citations", "accuracy"], category="research_eval"),
    BenchmarkCase("evaluator_agent",
                  "An output that repeats the question without providing answers.",
                  ["relevance", "Completeness", "score", "FAIL"], category="general_eval"),
    BenchmarkCase("evaluator_agent",
                  "A career roadmap tailored specifically to the user's background.",
                  ["relevance", "personalised", "score"], category="career_eval"),
    BenchmarkCase("evaluator_agent",
                  "A code review with improved code snippet that introduces a new bug.",
                  ["accuracy", "bug", "improved code"], category="code_eval"),
    BenchmarkCase("evaluator_agent",
                  "An agent output with high accuracy but poor formatting.",
                  ["structure", "formatting", "accuracy"], category="structure_eval"),
    BenchmarkCase("evaluator_agent",
                  "A research report with all High-confidence findings sourced correctly.",
                  ["confidence", "Accuracy", "Hallucination", "Low"], category="research_eval"),
    BenchmarkCase("evaluator_agent",
                  "An agent that used Tavily search but ignored all results.",
                  ["tool usage", "quality", "search"], category="tool_eval"),
    BenchmarkCase("evaluator_agent",
                  "A code review in the wrong programming language.",
                  ["relevance", "language", "score"], category="code_eval"),
    BenchmarkCase("evaluator_agent",
                  "A career output for a senior engineer when the user is a student.",
                  ["relevance", "experience level", "mismatch"], category="career_eval"),
    BenchmarkCase("evaluator_agent",
                  "An extremely long but comprehensive research report.",
                  ["Completeness", "structure", "score"], category="research_eval"),
    BenchmarkCase("evaluator_agent",
                  "A minimal one-paragraph response to a complex multi-part question.",
                  ["Completeness", "brevity", "gap"], category="general_eval"),
]

# ─────────────────────────────────────────────────────────────────────────────
# Benchmark Runner
# ─────────────────────────────────────────────────────────────────────────────

ALL_BENCHMARKS = (
    RESEARCH_BENCHMARKS
    + CAREER_BENCHMARKS
    + CODE_REVIEW_BENCHMARKS
    + EVALUATOR_BENCHMARKS
)


def get_benchmarks_by_agent(agent_name: str) -> List[BenchmarkCase]:
    return [b for b in ALL_BENCHMARKS if b.agent == agent_name]


def count_by_agent() -> dict:
    from collections import Counter
    return dict(Counter(b.agent for b in ALL_BENCHMARKS))


if __name__ == "__main__":
    print("📊 Benchmark Summary")
    print("=" * 40)
    for agent, count in count_by_agent().items():
        print(f"  {agent:<30} {count} test cases")
    print(f"  {'TOTAL':<30} {len(ALL_BENCHMARKS)} test cases")
    print()
    print("Run with: pytest evaluation/benchmarks.py -v")
    print("Or import get_benchmarks_by_agent() in your test suite.")