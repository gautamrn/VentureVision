from pydantic import BaseModel
from langchain_openai import ChatOpenAI

from app.graph.state import AgentState

MAX_ITERATIONS = 3


class CritiqueResult(BaseModel):
    is_sufficient: bool
    coverage_score: float
    feedback: str


llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, max_tokens=1024)
critic_llm = llm.with_structured_output(CritiqueResult)

SYSTEM_PROMPT = """You are a data quality auditor for a venture capital due diligence system.

You will receive:
1. The original research plan (search queries)
2. The evidence collected so far

Evaluate whether the evidence sufficiently covers the research plan.
- coverage_score: 0.0 to 1.0 representing what fraction of queries have meaningful results
- is_sufficient: true if coverage_score >= 0.8
- feedback: if not sufficient, output 2-4 NEW web search queries (comma-separated) that would fill the gaps. Write them as you would type into Google — specific and searchable. Example: "Stripe competitor Series A funding 2024, mobile payments Africa market size 2025, Square pricing small business"

Do NOT output prose like "missing competitor pricing data". Output actual search queries the agent can run."""


def critic_node(state: AgentState) -> dict:
    iteration = state.get("analysis_iteration", 0)

    if iteration >= MAX_ITERATIONS:
        return {"is_validated": True, "analysis_iteration": iteration}

    plan = state["research_plan"]
    evidence = state.get("raw_evidence", [])
    evidence_text = "\n".join(
        f"- [{e.query}] {e.title}: {e.snippet[:200]}" for e in evidence
    )

    try:
        result: CritiqueResult = critic_llm.invoke(
            [
                ("system", SYSTEM_PROMPT),
                (
                    "human",
                    f"Research Plan:\n{chr(10).join(plan)}\n\nEvidence Collected:\n{evidence_text}",
                ),
            ]
        )
        return {
            "is_validated": result.is_sufficient,
            "critique_feedback": result.feedback,
            "coverage_score": result.coverage_score,
            "analysis_iteration": iteration + 1,
        }
    except Exception:
        return {
            "is_validated": True,
            "critique_feedback": "",
            "coverage_score": 0.0,
            "analysis_iteration": iteration + 1,
        }
