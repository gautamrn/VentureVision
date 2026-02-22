# Venture-Vision: Technical Specification

## Core Objective
A multi-agent system for autonomous startup due diligence. The system must transform a raw pitch into a validated, data-backed Investment Memo.

## Agent Architecture (LangGraph)
1. **Planner:** Deconstructs pitch into discrete research vectors (JSON).
2. **Scout:** Parallelized web search via Tavily API. Filters for revenue, competitors, and market size.
3. **Critic:** Logic Gate. Compares Scout results vs. Planner vectors. If data density is < 80%, it triggers a recursive search loop with refined queries.
4. **Writer:** Synthesizes final state into a structured Markdown document.

## System Constraints
- **Data Grounding:** No hallucinations. All claims require a `source_url`.
- **State Persistence:** LangGraph must maintain a thread-safe state for the "Critic-Scout" loop.
- **Reliability:** Implement a 0.0-1.0 Confidence Score based on source diversity.