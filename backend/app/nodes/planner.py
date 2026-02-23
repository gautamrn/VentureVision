from pydantic import BaseModel
from langchain_openai import ChatOpenAI

from app.graph.state import AgentState


class ResearchPlan(BaseModel):
    queries: list[str]


llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, max_tokens=1024)
planner_llm = llm.with_structured_output(ResearchPlan)

SYSTEM_PROMPT_QUICK = """You are a due diligence research planner for a venture capital firm.

Given a startup pitch, decompose it into exactly 4 specific web search queries that would
help an analyst evaluate the opportunity. Focus on the highest-signal areas:
- Market size and growth rate
- Direct competitors, their pricing, and funding
- Revenue model validation or comparable business models
- Technology feasibility

Each query should be specific enough to return useful results from a search engine.
Do NOT include generic queries like "startup analysis". Be precise."""

SYSTEM_PROMPT_DEEP = """You are a due diligence research planner for a venture capital firm.

Given a startup pitch, decompose it into 6-8 specific web search queries that would
help an analyst validate every claim. Cover all angles:
- Market size and growth rate
- Direct competitors, their pricing, and funding
- Revenue model validation
- Technology feasibility
- Team background (if names are mentioned)
- Regulatory or legal risks
- Customer acquisition channels

Each query should be specific enough to return useful results from a search engine.
Do NOT include generic queries like "startup analysis". Be precise."""


def planner_node(state: AgentState) -> dict:
    pitch = state["pitch"]
    mode = state.get("mode", "quick_check")
    prompt = SYSTEM_PROMPT_DEEP if mode == "investor_ready" else SYSTEM_PROMPT_QUICK

    try:
        result: ResearchPlan = planner_llm.invoke(
            [
                ("system", prompt),
                ("human", f"Here is the startup pitch:\n\n{pitch}"),
            ]
        )
        queries = result.queries
    except Exception:
        words = pitch.split()[:6]
        topic = " ".join(words)
        queries = [
            f"{topic} market size",
            f"{topic} competitors funding",
            f"{topic} revenue model",
            f"{topic} technology feasibility",
        ]

    if mode != "investor_ready":
        queries = queries[:4]

    return {
        "research_plan": queries,
        "analysis_iteration": 0,
    }
