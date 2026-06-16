/**
 * Agentic AI Platform — Frontend Application
 */

const API = {
  async request(method, path, body) {
    const opts = { method, headers: { "Content-Type": "application/json" } };
    if (body) opts.body = JSON.stringify(body);
    const res = await fetch(path, opts);
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || `Request failed (${res.status})`);
    return data;
  },
  get: (path) => API.request("GET", path),
  post: (path, body) => API.request("POST", path, body),
};

const PAGES = {
  dashboard: { title: "Dashboard", subtitle: "Platform overview and system status" },
  workflow: { title: "Workflow", subtitle: "Full multi-agent pipeline with supervisor routing" },
  research: { title: "Research Agent", subtitle: "Web research with Tavily search and cited reports" },
  career: { title: "Career Agent", subtitle: "Resume analysis, skill gaps, and career roadmaps" },
  "code-review": { title: "Code Review Agent", subtitle: "Bug detection, security analysis, and performance review" },
  evaluator: { title: "Evaluator", subtitle: "Score any agent output against quality metrics" },
  history: { title: "Run History", subtitle: "Browse and inspect past agent executions" },
  prompts: { title: "Prompt Registry", subtitle: "Versioned prompts for all agents" },
};

const AGENT_LABELS = {
  research_agent: "Research",
  career_agent: "Career",
  code_review_agent: "Code Review",
  evaluator_agent: "Evaluator",
  supervisor_agent: "Supervisor",
};

// ── Utilities ────────────────────────────────────────────────────────────────

function esc(str) {
  const d = document.createElement("div");
  d.textContent = str ?? "";
  return d.innerHTML;
}

function toast(msg, type = "info") {
  const el = document.createElement("div");
  el.className = `toast toast-${type}`;
  el.textContent = msg;
  document.getElementById("toast-container").appendChild(el);
  setTimeout(() => el.remove(), 5000);
}

function renderMarkdown(text) {
  if (!text) return "<p class='empty-state'>No content.</p>";
  const html = marked.parse(text, { breaks: true });
  const div = document.createElement("div");
  div.className = "markdown-body";
  div.innerHTML = html;
  div.querySelectorAll("pre code").forEach((block) => hljs.highlightElement(block));
  return div.outerHTML;
}

function certClass(status) {
  if (!status) return "cert-fail";
  if (status.includes("PASS") && !status.includes("CONDITIONAL")) return "cert-pass";
  if (status.includes("CONDITIONAL")) return "cert-conditional";
  return "cert-fail";
}

function renderEvaluation(eval_) {
  if (!eval_) return "";
  const metrics = [
    ["Accuracy", eval_.accuracy],
    ["Completeness", eval_.completeness],
    ["Relevance", eval_.relevance],
    ["Structure", eval_.structure],
    ["Tool Usage", eval_.tool_usage_quality],
  ];
  const bars = metrics
    .map(
      ([label, val]) => `
    <div class="score-row">
      <span>${label}</span>
      <div class="score-bar"><div class="score-fill" style="width:${(val / 10) * 100}%"></div></div>
      <span>${val}/10</span>
    </div>`
    )
    .join("");

  return `
    <div class="eval-card">
      <div class="eval-header">
        <div>
          <div class="eval-score">${eval_.overall_score}<span style="font-size:16px;color:var(--text-muted)">/100</span></div>
          <div style="font-size:12px;color:var(--text-muted);margin-top:4px">Hallucination risk: ${esc(eval_.hallucination_risk)}</div>
        </div>
        <span class="cert-badge ${certClass(eval_.certification_status)}">${esc(eval_.certification_status)}</span>
      </div>
      <div class="score-bars">${bars}</div>
      ${
        eval_.strengths || eval_.weaknesses
          ? `<div class="eval-sw">
          <div><h4>Strengths</h4><p>${esc(eval_.strengths || "—")}</p></div>
          <div><h4>Weaknesses</h4><p>${esc(eval_.weaknesses || "—")}</p></div>
        </div>`
          : ""
      }
    </div>`;
}

function renderLoading(steps) {
  const stepHtml = (steps || ["Processing..."])
    .map((s, i) => `<div class="loading-step ${i === 0 ? "active" : ""}">${esc(s)}</div>`)
    .join("");
  return `<div class="loading-overlay"><div class="spinner"></div><div class="loading-text">Running agent pipeline...</div><div class="loading-steps">${stepHtml}</div></div>`;
}

function renderMetaChips(data) {
  const chips = [];
  if (data.run_id) chips.push(`<span class="meta-chip">Run <strong>#${data.run_id}</strong></span>`);
  if (data.agent_name || data.selected_agent)
    chips.push(`<span class="meta-chip">Agent <strong>${esc(AGENT_LABELS[data.agent_name || data.selected_agent] || data.agent_name || data.selected_agent)}</strong></span>`);
  if (data.prompt_version) chips.push(`<span class="meta-chip">Prompt <strong>${esc(data.prompt_version)}</strong></span>`);
  if (data.latency_ms != null) chips.push(`<span class="meta-chip">Latency <strong>${Math.round(data.latency_ms)}ms</strong></span>`);
  if (data.success != null) chips.push(`<span class="meta-chip"><span class="status-dot ${data.success ? "ok" : "fail"}"></span>${data.success ? "Success" : "Failed"}</span>`);
  return chips.length ? `<div class="result-meta">${chips.join("")}</div>` : "";
}

function showModal(title, html) {
  document.getElementById("modal-title").textContent = title;
  document.getElementById("modal-body").innerHTML = html;
  document.getElementById("modal").classList.remove("hidden");
}

function closeModal() {
  document.getElementById("modal").classList.add("hidden");
}

async function updateHealthBadge() {
  const badge = document.getElementById("health-badge");
  const banner = document.getElementById("offline-banner");
  try {
    const h = await API.get("/health");
    badge.className = "health-badge ok";
    const parts = ["Online"];
    if (!h.groq_configured) parts.push("Groq missing");
    if (!h.tavily_configured) parts.push("Tavily missing");
    badge.textContent = parts.join(" · ");
    if (!h.groq_configured || !h.tavily_configured) badge.className = "health-badge warn";
    if (banner) banner.classList.add("hidden");
    return h;
  } catch {
    badge.className = "health-badge error";
    badge.textContent = "API offline";
    if (banner) banner.classList.remove("hidden");
    return null;
  }
}

// ── Page Renderers ───────────────────────────────────────────────────────────

async function pageDashboard(container) {
  container.innerHTML = renderLoading(["Loading dashboard..."]);
  const [health, runs, prompts] = await Promise.all([
    API.get("/health").catch(() => null),
    API.get("/runs?limit=5").catch(() => []),
    API.get("/prompts").catch(() => ({})),
  ]);

  const agentCount = Object.keys(prompts).length;
  const totalVersions = Object.values(prompts).reduce((s, v) => s + v.length, 0);
  const successRate = runs.length ? Math.round((runs.filter((r) => r.success).length / runs.length) * 100) : 0;

  container.innerHTML = `
    <div class="grid grid-4" style="margin-bottom:24px">
      <div class="stat-card">
        <div class="stat-label">Platform</div>
        <div class="stat-value">v${health?.version || "1.0"}</div>
        <div class="stat-meta">${health?.status === "ok" ? "Operational" : "Offline"}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Agents</div>
        <div class="stat-value">${agentCount}</div>
        <div class="stat-meta">${totalVersions} prompt versions</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Recent Runs</div>
        <div class="stat-value">${runs.length}</div>
        <div class="stat-meta">${successRate}% success rate</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">API Keys</div>
        <div class="stat-value">${health?.groq_configured && health?.tavily_configured ? "Ready" : "Partial"}</div>
        <div class="stat-meta">Groq ${health?.groq_configured ? "OK" : "Missing"} · Tavily ${health?.tavily_configured ? "OK" : "Missing"}</div>
      </div>
    </div>

    <div class="card" style="margin-bottom:24px">
      <div class="card-header"><h3>Agent Pipeline</h3></div>
      <div class="pipeline">
        <span class="pipeline-node">User Input</span>
        <span class="pipeline-arrow">→</span>
        <span class="pipeline-node highlight">Supervisor</span>
        <span class="pipeline-arrow">→</span>
        <span class="pipeline-node">Research</span>
        <span class="pipeline-node">Career</span>
        <span class="pipeline-node">Code Review</span>
        <span class="pipeline-arrow">→</span>
        <span class="pipeline-node highlight">Evaluator</span>
        <span class="pipeline-arrow">→</span>
        <span class="pipeline-node">Final Report</span>
      </div>
    </div>

    <div class="grid grid-2">
      <div class="card">
        <div class="card-header"><h3>Quick Actions</h3></div>
        <div class="btn-group">
          <a href="#workflow" class="btn btn-primary">Run Workflow</a>
          <a href="#research" class="btn btn-secondary">Research</a>
          <a href="#career" class="btn btn-secondary">Career</a>
          <a href="#code-review" class="btn btn-secondary">Code Review</a>
        </div>
      </div>
      <div class="card">
        <div class="card-header"><h3>Recent Runs</h3><a href="#history" class="btn btn-sm btn-secondary">View All</a></div>
        ${
          runs.length
            ? `<div class="table-wrap"><table class="data-table"><thead><tr><th>Agent</th><th>Task</th><th>Status</th></tr></thead><tbody>${runs
                .map(
                  (r) => `<tr style="cursor:pointer" data-run-id="${r.id}">
                <td><span class="agent-tag">${esc(AGENT_LABELS[r.agent_name] || r.agent_name)}</span></td>
                <td>${esc(r.task.slice(0, 60))}${r.task.length > 60 ? "..." : ""}</td>
                <td><span class="status-dot ${r.success ? "ok" : "fail"}"></span></td>
              </tr>`
                )
                .join("")}</tbody></table></div>`
            : `<div class="empty-state"><p>No runs yet. Start a workflow to see history.</p></div>`
        }
      </div>
    </div>`;

  container.querySelectorAll("[data-run-id]").forEach((row) => {
    row.addEventListener("click", () => viewRunDetail(parseInt(row.dataset.runId)));
  });
}

function pageWorkflow(container) {
  container.innerHTML = `
    <div class="card">
      <p style="color:var(--text-muted);font-size:14px;margin-bottom:20px">
        Enter any request. The supervisor will route it to the best agent, then the evaluator scores the result.
      </p>
      <div class="chat-container">
        <div id="workflow-messages" class="chat-messages"></div>
        <div class="chat-input-row">
          <textarea id="workflow-input" placeholder="Ask anything — research topics, career advice, or paste code for review..." rows="3"></textarea>
          <button class="btn btn-primary" id="workflow-run">Run</button>
        </div>
      </div>
      <div id="workflow-result"></div>
    </div>`;

  const input = document.getElementById("workflow-input");
  const result = document.getElementById("workflow-result");
  const messages = document.getElementById("workflow-messages");

  document.getElementById("workflow-run").addEventListener("click", async () => {
    const text = input.value.trim();
    if (text.length < 3) return toast("Enter at least 3 characters", "error");

    messages.innerHTML += `<div class="chat-msg user"><div class="chat-msg-label">You</div><p>${esc(text)}</p></div>`;
    result.innerHTML = renderLoading(["Supervisor routing...", "Running specialist agent...", "Evaluating output..."]);
    input.value = "";

    try {
      const data = await API.post("/run", { user_input: text });
      result.innerHTML = `
        ${renderMetaChips({ ...data, agent_name: data.selected_agent })}
        ${data.task_summary ? `<p style="font-size:13px;color:var(--text-muted);margin-bottom:12px"><strong>Task:</strong> ${esc(data.task_summary)}</p>` : ""}
        <div class="result-panel">
          <h3 style="margin-bottom:12px;font-size:15px">Agent Response</h3>
          ${renderMarkdown(data.result || data.final_report)}
          ${renderEvaluation(data.evaluation)}
        </div>`;
      messages.innerHTML += `<div class="chat-msg assistant"><div class="chat-msg-label">${esc(AGENT_LABELS[data.selected_agent] || "Agent")}</div>${renderMarkdown(data.result)}</div>`;
      updateHealthBadge();
    } catch (err) {
      result.innerHTML = `<div class="empty-state"><h3>Error</h3><p>${esc(err.message)}</p></div>`;
      toast(err.message, "error");
    }
  });

  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) document.getElementById("workflow-run").click();
  });
}

function pageResearch(container) {
  container.innerHTML = `
    <div class="card">
      <form id="research-form">
        <div class="form-group">
          <label>Research Topic</label>
          <textarea id="research-task" placeholder="What is retrieval-augmented generation?" required></textarea>
        </div>
        <div class="form-row form-row-3">
          <div class="form-group">
            <label>Search Depth</label>
            <select id="research-depth"><option value="advanced">Advanced</option><option value="basic">Basic</option></select>
          </div>
          <div class="form-group">
            <label>Max Results</label>
            <input type="number" id="research-max" value="5" min="1" max="10" />
          </div>
          <div class="form-group">
            <label>Summary Length</label>
            <select id="research-length"><option value="standard">Standard</option><option value="brief">Brief</option><option value="detailed">Detailed</option></select>
          </div>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label>Prompt Version</label>
            <select id="research-prompt"><option value="">Default (v3)</option><option value="v1">v1</option><option value="v2">v2</option><option value="v3">v3</option></select>
          </div>
          <div class="form-group">
            <label>Temperature</label>
            <input type="number" id="research-temp" value="0.1" min="0" max="1" step="0.1" />
          </div>
        </div>
        <button type="submit" class="btn btn-primary">Run Research</button>
      </form>
      <div id="research-result"></div>
    </div>`;

  document.getElementById("research-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const el = document.getElementById("research-result");
    el.innerHTML = renderLoading(["Searching web...", "Synthesizing report...", "Evaluating..."]);
    try {
      const body = {
        task: document.getElementById("research-task").value.trim(),
        search_depth: document.getElementById("research-depth").value,
        max_results: parseInt(document.getElementById("research-max").value),
        summary_length: document.getElementById("research-length").value,
        temperature: parseFloat(document.getElementById("research-temp").value),
      };
      const pv = document.getElementById("research-prompt").value;
      if (pv) body.prompt_version = pv;
      const data = await API.post("/agents/research", body);
      el.innerHTML = `${renderMetaChips(data)}<div class="result-panel">${renderMarkdown(data.result)}${renderEvaluation(data.evaluation)}</div>`;
      if (!data.success) toast(data.result || "Research agent failed", "error");
    } catch (err) {
      el.innerHTML = `<div class="empty-state"><h3>Error</h3><p>${esc(err.message)}</p></div>`;
      toast(err.message, "error");
    }
  });
}

function pageCareer(container) {
  container.innerHTML = `
    <div class="card">
      <form id="career-form">
        <div class="form-group">
          <label>Resume or Career Question</label>
          <textarea id="career-task" placeholder="I'm a 3rd year CS student with Python skills. I want to become an ML Engineer." required rows="5"></textarea>
        </div>
        <div class="form-row form-row-3">
          <div class="form-group">
            <label>Experience Level</label>
            <select id="career-level"><option value="student">Student</option><option value="junior">Junior</option><option value="mid">Mid</option><option value="senior">Senior</option></select>
          </div>
          <div class="form-group">
            <label>Career Target</label>
            <input type="text" id="career-target" value="AI Engineer" />
          </div>
          <div class="form-group">
            <label>Industry Focus</label>
            <input type="text" id="career-industry" value="AI startups" />
          </div>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label>Recommendation Depth</label>
            <select id="career-depth"><option value="standard">Standard</option><option value="shallow">Shallow</option><option value="deep">Deep</option></select>
          </div>
          <div class="form-group">
            <label>Prompt Version</label>
            <select id="career-prompt"><option value="">Default (v2)</option><option value="v1">v1</option><option value="v2">v2</option></select>
          </div>
        </div>
        <button type="submit" class="btn btn-primary">Get Career Advice</button>
      </form>
      <div id="career-result"></div>
    </div>`;

  document.getElementById("career-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const el = document.getElementById("career-result");
    el.innerHTML = renderLoading(["Analyzing profile...", "Generating roadmap...", "Evaluating..."]);
    try {
      const body = {
        task: document.getElementById("career-task").value.trim(),
        experience_level: document.getElementById("career-level").value,
        career_target: document.getElementById("career-target").value,
        industry_focus: document.getElementById("career-industry").value,
        recommendation_depth: document.getElementById("career-depth").value,
      };
      const pv = document.getElementById("career-prompt").value;
      if (pv) body.prompt_version = pv;
      const data = await API.post("/agents/career", body);
      el.innerHTML = `${renderMetaChips(data)}<div class="result-panel">${renderMarkdown(data.result)}${renderEvaluation(data.evaluation)}</div>`;
    } catch (err) {
      el.innerHTML = `<div class="empty-state"><h3>Error</h3><p>${esc(err.message)}</p></div>`;
      toast(err.message, "error");
    }
  });
}

function pageCodeReview(container) {
  container.innerHTML = `
    <div class="card">
      <form id="code-form">
        <div class="form-group">
          <label>Code to Review</label>
          <textarea id="code-input" class="code-input" placeholder="Paste your code here..." required>def get_user(name):
    return db.execute(f"SELECT * FROM users WHERE name={name}")</textarea>
        </div>
        <div class="form-row form-row-3">
          <div class="form-group">
            <label>Strictness</label>
            <select id="code-strict"><option value="standard">Standard</option><option value="lenient">Lenient</option><option value="strict">Strict</option></select>
          </div>
          <div class="form-group">
            <label>Language (optional)</label>
            <input type="text" id="code-lang" placeholder="Auto-detect" />
          </div>
          <div class="form-group">
            <label>Explanation Detail</label>
            <select id="code-detail"><option value="standard">Standard</option><option value="minimal">Minimal</option><option value="verbose">Verbose</option></select>
          </div>
        </div>
        <div class="form-row">
          <label class="checkbox-row"><input type="checkbox" id="code-security" checked /> Security focus</label>
          <label class="checkbox-row"><input type="checkbox" id="code-perf" checked /> Performance focus</label>
        </div>
        <button type="submit" class="btn btn-primary" style="margin-top:12px">Review Code</button>
      </form>
      <div id="code-result"></div>
    </div>`;

  document.getElementById("code-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const el = document.getElementById("code-result");
    el.innerHTML = renderLoading(["Analyzing code...", "Checking security...", "Evaluating..."]);
    try {
      const body = {
        code: document.getElementById("code-input").value,
        strictness_level: document.getElementById("code-strict").value,
        explanation_detail: document.getElementById("code-detail").value,
        security_focus: document.getElementById("code-security").checked,
        performance_focus: document.getElementById("code-perf").checked,
      };
      const lang = document.getElementById("code-lang").value.trim();
      if (lang) body.language = lang;
      const data = await API.post("/agents/code-review", body);
      el.innerHTML = `${renderMetaChips(data)}<div class="result-panel">${renderMarkdown(data.result)}${renderEvaluation(data.evaluation)}</div>`;
    } catch (err) {
      el.innerHTML = `<div class="empty-state"><h3>Error</h3><p>${esc(err.message)}</p></div>`;
      toast(err.message, "error");
    }
  });
}

function pageEvaluator(container) {
  container.innerHTML = `
    <div class="card">
      <form id="eval-form">
        <div class="form-group">
          <label>Agent Output Text</label>
          <textarea id="eval-text" placeholder="Paste agent output to evaluate..." required rows="8"></textarea>
        </div>
        <div class="form-row form-row-3">
          <div class="form-group">
            <label>Agent Name</label>
            <select id="eval-agent">
              <option value="research_agent">Research</option>
              <option value="career_agent">Career</option>
              <option value="code_review_agent">Code Review</option>
              <option value="unknown_agent">Other</option>
            </select>
          </div>
          <div class="form-group">
            <label>Prompt Version</label>
            <input type="text" id="eval-prompt" value="v1" />
          </div>
          <div class="form-group">
            <label>Original Task</label>
            <input type="text" id="eval-task" value="Not specified" />
          </div>
        </div>
        <button type="submit" class="btn btn-primary">Evaluate Output</button>
      </form>
      <div id="eval-result"></div>
    </div>`;

  document.getElementById("eval-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const el = document.getElementById("eval-result");
    el.innerHTML = renderLoading(["Scoring output..."]);
    try {
      const data = await API.post("/evaluate", {
        agent_output_text: document.getElementById("eval-text").value.trim(),
        agent_name: document.getElementById("eval-agent").value,
        prompt_version: document.getElementById("eval-prompt").value,
        task: document.getElementById("eval-task").value,
      });
      el.innerHTML = `<div class="result-panel">${renderEvaluation(data)}</div>`;
    } catch (err) {
      el.innerHTML = `<div class="empty-state"><h3>Error</h3><p>${esc(err.message)}</p></div>`;
      toast(err.message, "error");
    }
  });
}

async function pageHistory(container) {
  container.innerHTML = renderLoading(["Loading run history..."]);
  let runs = [];
  try {
    runs = await API.get("/runs?limit=50");
  } catch (err) {
    container.innerHTML = `<div class="empty-state"><h3>Error</h3><p>${esc(err.message)}</p></div>`;
    return;
  }

  const agents = [...new Set(runs.map((r) => r.agent_name))];

  container.innerHTML = `
    <div class="filter-bar">
      <label style="font-size:13px;color:var(--text-muted)">Filter by agent:</label>
      <select id="history-filter">
        <option value="">All agents</option>
        ${agents.map((a) => `<option value="${a}">${esc(AGENT_LABELS[a] || a)}</option>`).join("")}
      </select>
      <button class="btn btn-sm btn-secondary" id="history-refresh">Refresh</button>
    </div>
    ${
      runs.length
        ? `<div class="table-wrap"><table class="data-table" id="history-table">
        <thead><tr><th>ID</th><th>Agent</th><th>Task</th><th>Prompt</th><th>Latency</th><th>Status</th><th>Date</th><th></th></tr></thead>
        <tbody>${runs
          .map(
            (r) => `<tr data-agent="${r.agent_name}">
          <td>#${r.id}</td>
          <td><span class="agent-tag">${esc(AGENT_LABELS[r.agent_name] || r.agent_name)}</span></td>
          <td>${esc(r.task.slice(0, 50))}${r.task.length > 50 ? "..." : ""}</td>
          <td>${esc(r.prompt_version)}</td>
          <td>${Math.round(r.latency_ms)}ms</td>
          <td><span class="status-dot ${r.success ? "ok" : "fail"}"></span></td>
          <td style="font-size:12px;color:var(--text-muted)">${new Date(r.created_at).toLocaleString()}</td>
          <td><button class="btn btn-sm btn-secondary" data-view-run="${r.id}">View</button></td>
        </tr>`
          )
          .join("")}</tbody></table></div>`
        : `<div class="empty-state"><h3>No runs yet</h3><p>Execute a workflow or agent to see history here.</p></div>`
    }`;

  document.getElementById("history-filter")?.addEventListener("change", (e) => {
    const val = e.target.value;
    document.querySelectorAll("#history-table tbody tr").forEach((row) => {
      row.style.display = !val || row.dataset.agent === val ? "" : "none";
    });
  });

  document.getElementById("history-refresh")?.addEventListener("click", () => navigate("history"));
  container.querySelectorAll("[data-view-run]").forEach((btn) => {
    btn.addEventListener("click", () => viewRunDetail(parseInt(btn.dataset.viewRun)));
  });
}

async function viewRunDetail(runId) {
  try {
    const run = await API.get(`/runs/${runId}`);
    showModal(
      `Run #${run.id} — ${AGENT_LABELS[run.agent_name] || run.agent_name}`,
      `
      ${renderMetaChips(run)}
      <div style="margin:16px 0"><strong style="font-size:13px;color:var(--text-muted)">Task</strong><p style="margin-top:6px">${esc(run.task)}</p></div>
      <div style="margin-bottom:16px"><strong style="font-size:13px;color:var(--text-muted)">Result</strong>${renderMarkdown(run.result)}</div>
      ${run.metadata ? `<div style="margin-bottom:16px"><strong style="font-size:13px;color:var(--text-muted)">Metadata</strong><pre style="font-size:12px;background:var(--bg-elevated);padding:12px;border-radius:8px;margin-top:6px;overflow:auto">${esc(JSON.stringify(run.metadata, null, 2))}</pre></div>` : ""}
      ${renderEvaluation(run.evaluation)}`
    );
  } catch (err) {
    toast(err.message, "error");
  }
}

async function pagePrompts(container) {
  container.innerHTML = renderLoading(["Loading prompts..."]);
  let prompts = {};
  try {
    prompts = await API.get("/prompts");
  } catch (err) {
    container.innerHTML = `<div class="empty-state"><h3>Error</h3><p>${esc(err.message)}</p></div>`;
    return;
  }

  const agentCards = Object.entries(prompts)
    .map(
      ([agent, versions]) => `
    <div class="prompt-agent-card">
      <div class="prompt-agent-header">${esc(AGENT_LABELS[agent] || agent)}</div>
      <div class="prompt-versions">
        ${versions
          .map(
            (v) => `<div class="version-item">
          <span class="ver">${esc(v.version)}</span>
          <span class="notes">${esc(v.notes)}</span>
        </div>`
          )
          .join("")}
      </div>
    </div>`
    )
    .join("");

  container.innerHTML = `
    <div class="prompt-grid" style="margin-bottom:24px">${agentCards}</div>
    <div class="card">
      <div class="card-header"><h3>Compare Prompt Versions</h3></div>
      <div class="form-row form-row-3">
        <div class="form-group">
          <label>Agent</label>
          <select id="compare-agent">${Object.keys(prompts)
            .map((a) => `<option value="${a}">${esc(AGENT_LABELS[a] || a)}</option>`)
            .join("")}</select>
        </div>
        <div class="form-group">
          <label>Version A</label>
          <select id="compare-a"></select>
        </div>
        <div class="form-group">
          <label>Version B</label>
          <select id="compare-b"></select>
        </div>
      </div>
      <button class="btn btn-primary" id="compare-btn">Compare</button>
      <div id="compare-result"></div>
    </div>`;

  function updateVersionSelects() {
    const agent = document.getElementById("compare-agent").value;
    const versions = prompts[agent] || [];
    const opts = versions.map((v) => `<option value="${v.version}">${v.version}</option>`).join("");
    document.getElementById("compare-a").innerHTML = opts;
    document.getElementById("compare-b").innerHTML = opts;
    if (versions.length > 1) document.getElementById("compare-b").selectedIndex = 1;
  }

  document.getElementById("compare-agent").addEventListener("change", updateVersionSelects);
  updateVersionSelects();

  document.getElementById("compare-btn").addEventListener("click", async () => {
    const el = document.getElementById("compare-result");
    el.innerHTML = renderLoading(["Loading comparison..."]);
    try {
      const data = await API.post("/prompts/compare", {
        agent: document.getElementById("compare-agent").value,
        version_a: document.getElementById("compare-a").value,
        version_b: document.getElementById("compare-b").value,
      });
      el.innerHTML = `
        <div class="compare-panel" style="margin-top:20px">
          <div class="compare-col">
            <div class="compare-col-header">${esc(data.version_a.version)} — ${esc(data.version_a.notes)}</div>
            <div class="compare-prompt">${esc(data.version_a.prompt)}</div>
          </div>
          <div class="compare-col">
            <div class="compare-col-header">${esc(data.version_b.version)} — ${esc(data.version_b.notes)}</div>
            <div class="compare-prompt">${esc(data.version_b.prompt)}</div>
          </div>
        </div>`;
    } catch (err) {
      el.innerHTML = `<div class="empty-state"><p>${esc(err.message)}</p></div>`;
      toast(err.message, "error");
    }
  });
}

// ── Router ───────────────────────────────────────────────────────────────────

const PAGE_RENDERERS = {
  dashboard: pageDashboard,
  workflow: pageWorkflow,
  research: pageResearch,
  career: pageCareer,
  "code-review": pageCodeReview,
  evaluator: pageEvaluator,
  history: pageHistory,
  prompts: pagePrompts,
};

function navigate(page) {
  const p = PAGES[page] ? page : "dashboard";
  window.location.hash = p;

  document.querySelectorAll(".nav-link").forEach((link) => {
    link.classList.toggle("active", link.dataset.page === p);
  });

  document.getElementById("page-title").textContent = PAGES[p].title;
  document.getElementById("page-subtitle").textContent = PAGES[p].subtitle;

  const container = document.getElementById("page-content");
  const renderer = PAGE_RENDERERS[p];
  if (renderer) renderer(container);

  document.getElementById("sidebar").classList.remove("open");
}

function initRouter() {
  const page = window.location.hash.slice(1) || "dashboard";
  navigate(PAGES[page] ? page : "dashboard");
  window.addEventListener("hashchange", () => {
    const p = window.location.hash.slice(1) || "dashboard";
    navigate(PAGES[p] ? p : "dashboard");
  });
}

// ── Init ─────────────────────────────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", () => {
  initRouter();
  updateHealthBadge();
  setInterval(updateHealthBadge, 30000);

  document.getElementById("menu-toggle").addEventListener("click", () => {
    document.getElementById("sidebar").classList.toggle("open");
  });

  document.querySelectorAll("[data-close-modal]").forEach((el) => {
    el.addEventListener("click", closeModal);
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeModal();
  });
});
