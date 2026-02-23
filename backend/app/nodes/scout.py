from tavily import TavilyClient
from app.graph.state import AgentState
from app.schemas.models import EvidenceItem
import os

tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))


def scout_node(state: AgentState) -> dict:
    queries = state["research_plan"]
    feedback = state.get("critique_feedback", "")

    if feedback:
        feedbackQueries = [q.strip() for q in feedback.split(",") if q.strip()]
        if not feedbackQueries:
            feedbackQueries = [feedback.strip()]
        queries = feedbackQueries[:4]

    evidence: list[EvidenceItem] = state.get("raw_evidence", [])

    for query in queries:
        try:
            response = tavily.search(
                query=query,
                max_results=2,
                include_answer=True,
                topic="general",
            )
        except Exception:
            continue

        answer = response.get("answer", "")

        for result in response.get("results", []):
            snippet = result.get("content", "")[:800]
            if answer and len(snippet) < 200:
                snippet = f"{snippet} | Summary: {answer[:300]}"

            evidence.append(
                EvidenceItem(
                    query=query,
                    title=result.get("title", ""),
                    snippet=snippet,
                    source_url=result.get("url", ""),
                )
            )

    return {"raw_evidence": evidence}
