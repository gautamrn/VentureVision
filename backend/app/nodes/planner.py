from pydantic import BaseModel
from langchain_anthropic import ChatAnthropic

from app.graph.state import AgentState


class ResearchPlan(BaseModel):
    queries: list[str]


llm = ChatAnthropic(model="claude-sonnet-4-5", temperature=0, max_tokens=1024)
planner_llm = llm.with_structured_output(ResearchPlan)

SYSTEM_PROMPT = """You are a due diligence research planner for a venture capital firm.

Given a startup pitch, decompose it into 5-8 specific web search queries that would
help an analyst validate the claims. Focus on:
- Market size and growth rate
- Direct competitors, their pricing, and funding
- Revenue model validation
- Technology feasibility
- Team background (if names are mentioned)

Each query should be specific enough to return useful results from a search engine.
Do NOT include generic queries like "startup analysis". Be precise."""


def planner_node(state: AgentState) -> dict:
    pitch = state["pitch"]

    result: ResearchPlan = planner_llm.invoke(
        [
            ("system", SYSTEM_PROMPT),
            ("human", f"Here is the startup pitch:\n\n{pitch}"),
        ]
    )

    return {
        "research_plan": result.queries,
        "analysis_iteration": 0,
    }
