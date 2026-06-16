# `agents/research_agent.py` — Line-by-Line Explanation

**File:** `agents/research_agent.py`  
**Role:** Implements the `ResearchAgent`, which uses LangChain tool-calling to browse the web (via Tavily) and synthesize evidence-backed reports.

---

## Class Definition and Init (Lines 28–53)

```python
class ResearchAgent(BaseAgent):
    """
    Searches the web, synthesises information, and returns a
    structured Markdown report with citations.
    """

    agent_name = "research_agent"
    version = "1.0"

    def __init__(
        self,
        prompt_version: Optional[str] = None,
        search_depth: str = "advanced",
        max_results: int = 5,
        summary_length: str = "standard",
        temperature: float = 0.1,  # Low temp for factual accuracy
    ):
        super().__init__(prompt_version=prompt_version, temperature=temperature)

        self.search_depth = search_depth
        self.max_results = max_results
        self.summary_length = summary_length

        self._default_tool = self._make_search_tool(search_depth, max_results)
```

- **Inherits from `BaseAgent`**.
- Sets parameters specific to research operations (`search_depth`, `max_results`).
- `temperature=0.1`: Research needs to be highly factual and grounded, so hallucination-inducing creativity is turned off.
- `self._default_tool`: Instantiates a Tavily search tool configured with the provided default settings.

---

## Tool Factory `_make_search_tool` (Lines 55–71)

```python
    def _make_search_tool(self, depth: str, k: int) -> TavilySearchResults:
        """Build a configured Tavily tool."""
        settings = get_settings()
        if settings.tavily_api_key:
            os.environ.setdefault("TAVILY_API_KEY", settings.tavily_api_key)
        return TavilySearchResults(
            max_results=k,
            search_depth=depth,
            include_answer=True,
            include_raw_content=False,
            include_images=False,
        )
```

- Creates and returns a `TavilySearchResults` LangChain tool.
- **Hack/Workaround**: The LangChain Tavily wrapper historically hard-reads `os.environ["TAVILY_API_KEY"]` rather than accepting it as an argument easily. This method explicitly injects the key from `config.Settings` into `os.environ` just to be safe.
- Disables raw content and images to save LLM context window tokens.

---

## Execution Method `run` (Lines 73–170)

```python
    async def run(
        self,
        task: str,
        # ... overrides ...
    ) -> AgentOutput:
        start = time.perf_counter()
        
        # ... variable resolution ...

        try:
            tool = self._make_search_tool(depth, k)

            length_hint = {
                "brief":    "Keep the summary under 150 words.",
                "standard": "Write a thorough but focused summary (200-350 words).",
                "detailed": "Write a comprehensive, detailed summary (400+ words).",
            }.get(length, "")

            augmented_system = self.system_prompt + f"\n\nSUMMARY LENGTH INSTRUCTION: {length_hint}"
```

- Resolves overrides and builds a fresh `tool` instance for this specific run so that per-request settings (like `max_results=10`) are honored.
- Appends the summary length instruction to the system prompt.

```python
            messages = [
                SystemMessage(content=augmented_system),
                HumanMessage(content=f"Research task: {task}"),
            ]

            # Use tool calling for a reliable search → synthesise loop
            llm_with_tools = self.llm.bind_tools([tool])

            # Step 1: Let the LLM decide what to search for
            ai_msg = await llm_with_tools.ainvoke(messages)
```

- **`bind_tools([tool])`**: Instructs the LLM that it has a tool available it can call.
- **Step 1**: The first invocation does *not* return the final report. Instead, the LLM analyzes the task and outputs a special message requesting to execute a tool (e.g., "search for X").

```python
            # Step 2: Execute any tool calls
            search_results = []
            tool_messages = []

            if ai_msg.tool_calls:
                for tool_call in ai_msg.tool_calls:
                    query = tool_call["args"].get("query", task)
                    self.log.debug("research_agent.search", query=query)
                    result = await tool.ainvoke({"query": query})
                    search_results.extend(result if isinstance(result, list) else [result])
                    
                    from langchain_core.messages import ToolMessage
                    tool_messages.append(
                        ToolMessage(content=str(result), tool_call_id=tool_call["id"])
                    )
```

- **Step 2**: If the LLM decided to use the tool, the code iterates over its requested `tool_calls`.
- It executes `tool.ainvoke` (the actual web API request to Tavily).
- It takes the JSON results and wraps them in a LangChain `ToolMessage`. The `tool_call_id` is critical—it tells the LLM "here is the answer to the specific tool call you just requested".

```python
            # Step 3: Synthesise the final report
            synthesis_messages = messages + [ai_msg] + tool_messages + [
                HumanMessage(
                    content=(
                        "Now write the final structured research report based on "
                        "the search results above. Follow the exact output format "
                        "specified in your system instructions."
                    )
                )
            ]

            final = await self.llm.ainvoke(synthesis_messages)
            report = final.content
```

- **Step 3**: Re-assembles the conversation history. It includes:
  1. The original system and human prompts.
  2. The LLM's `ai_msg` (where it requested the tool).
  3. The `tool_messages` (the raw search results).
  4. A final human nudge telling the LLM to write the report now that it has the data.
- Executes the LLM a second time (`ainvoke`). This time, the LLM reads the search results and synthesizes the final markdown report.
- Returns the `AgentOutput` packaged with detailed metadata about how many tool calls were made and how many sources were retrieved.
