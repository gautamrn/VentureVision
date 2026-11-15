from pydantic import BaseModel
from langchain_openai import ChatOpenAI

from app.graph.state import AgentState
from app.telemetry.usage import ModelOutputError, invokeStructured, structuredOutput


class ResearchPlan(BaseModel):
    queries: list[str]


llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, max_tokens=1024)
planner_llm = structuredOutput(llm, ResearchPlan)

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

SYSTEM_PROMPT_PITCH_LAB = """You are a web search query generator. A founder wrote a startup pitch and needs data to make it stronger. Generate 6-8 search queries that find specific facts, figures, and competitor details the founder can cite in their pitch.

Write queries the way you would actually type them into Google — specific, with real keywords.

GOOD queries: "pet care marketplace market size 2025 revenue report", "Rover Wag funding round valuation 2024", "dog walking app pricing comparison monthly subscription", "on-demand pet services customer acquisition cost"
BAD queries: "startup analysis", "market size", "competitors funding"

The goal is to find DATA the founder can put in their pitch:
- Market size figures with dollar amounts and growth rates
- Competitor names, funding rounds, pricing models
- Industry-specific metrics (CAC, LTV, conversion rates)
- Regulatory or compliance requirements in this space

Rules:
- Extract specific product names, company names, industry terms, and technologies from the pitch
- Include years (2024, 2025) for recent data
- 2 queries should target market size with specific dollar figures
- 2 queries should target direct competitors by name + their funding/pricing
- 1 query should target comparable business models and revenue metrics
- 1-2 queries should explore gaps: regulatory landscape, customer behavior, or technology feasibility
- Each query should be specific enough to return citable data points"""


def planner_node(state: AgentState) -> dict:
    pitch = state["pitch"]
    mode = state.get("mode", "market_scan")
    prompt = SYSTEM_PROMPT_PITCH_LAB if mode == "pitch_lab" else SYSTEM_PROMPT_QUICK

    result, _ = invokeStructured(
        planner_llm,
        [
            ("system", prompt),
            ("human", f"Here is the startup pitch:\n\n{pitch}"),
        ],
    )
    queries = [q for q in result.queries if q.strip()]
    if not queries:
        raise ModelOutputError("planner returned no search queries")

    if mode != "pitch_lab":
        queries = queries[:4]

    return {
        "research_plan": queries,
        "analysis_iteration": 0,
    }
