from tavily import TavilyClient
from app.graph.state import AgentState
from app.schemas.models import EvidenceItem
import os

tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))


def scout_node(state: AgentState) -> dict:
    queries = state["research_plan"]
    feedback = state.get("critique_feedback", "")

    if feedback:
        queries = [f"{q} {feedback}" for q in queries[:3]]

    evidence: list[EvidenceItem] = state.get("raw_evidence", [])

    for query in queries:
        response = tavily.search(query=query, max_results=2)

        for result in response.get("results", []):
            evidence.append(
                EvidenceItem(
                    query=query,
                    title=result.get("title", ""),
                    snippet=result.get("content", "")[:500],
                    source_url=result.get("url", ""),
                )
            )

    return {"raw_evidence": evidence}
