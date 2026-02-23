from pydantic import BaseModel
from langchain_openai import ChatOpenAI

from app.graph.state import AgentState


class ResearchPlan(BaseModel):
    queries: list[str]


llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, max_tokens=1024)
planner_llm = llm.with_structured_output(ResearchPlan)

SYSTEM_PROMPT_QUICK = """You are a web search query generator for market research.

Given a startup idea, generate exactly 4 search queries that would help someone understand the market landscape. Write queries the way you would actually type them into Google — specific, with real keywords.

GOOD queries (specific, searchable):
- "dog walking app competitors funding 2024 2025"
- "pet care marketplace market size revenue"
- "Rover Wag pricing comparison dog walking"
- "on-demand pet services startup funding rounds"

BAD queries (too generic, won't return useful results):
- "dog walking market size"
- "competitors in pet care"
- "startup analysis dog walking"

Rules:
- Extract specific product names, company names, or industry terms from the pitch and use them in queries
- Include years (2024, 2025) in market size queries for recent data
- One query should target direct competitors by name if identifiable from the pitch
- One query should target market size with specific industry terms
- One query should look for comparable business models or pricing
- One query should explore the specific problem space or technology"""

SYSTEM_PROMPT_DEEP = """You are a web search query generator for deep market research.

Given a startup pitch, generate 6-8 search queries that would help a VC analyst validate the opportunity from every angle. Write queries the way you would actually type them into Google — specific, with real keywords.

GOOD queries: "fintech payments API unbanked market size 2025", "Stripe competitor funding series A B", "mobile money Africa revenue model pricing"
BAD queries: "startup analysis", "market size", "competitors funding"

Rules:
- Extract specific product names, company names, industry terms, and technologies from the pitch
- Include years (2024, 2025) for recent data
- Cover: market size, direct competitors + funding, pricing/revenue models, technology feasibility
- Also cover: regulatory risks, customer acquisition channels, team backgrounds (if names mentioned)
- Each query should be specific enough to return actionable results from a search engine"""


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
