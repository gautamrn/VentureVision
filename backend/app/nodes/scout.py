from datetime import datetime, timezone

from tavily import TavilyClient
from app.graph.state import AgentState
from app.nodes.queries import parseFeedbackQueries
from app.schemas.models import EvidenceItem
from app.telemetry.usage import recordSearch
import os

tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))


def scout_node(state: AgentState) -> dict:
    queries = state["research_plan"]
    feedback = state.get("critique_feedback", "")

    if feedback:
        queries = parseFeedbackQueries(feedback)

    evidence: list[EvidenceItem] = list(state.get("raw_evidence", []))

    for query in queries:
        try:
            response = tavily.search(
                query=query,
                max_results=2,
                include_answer=True,
                topic="general",
            )
        except Exception as exc:
            recordSearch(query, resultCount=0, error=type(exc).__name__)
            continue

        retrievedAt = datetime.now(timezone.utc)
        answer = response.get("answer", "")
        results = response.get("results", [])
        recordSearch(query, resultCount=len(results))

        for result in results:
            snippet = result.get("content", "")[:800]
            if answer and len(snippet) < 200:
                snippet = f"{snippet} | Summary: {answer[:300]}"

            evidence.append(
                EvidenceItem(
                    query=query,
                    title=result.get("title", ""),
                    snippet=snippet,
                    source_url=result.get("url", ""),
                    retrieved_at=retrievedAt,
                )
            )

    return {"raw_evidence": evidence}
