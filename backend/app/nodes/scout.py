from datetime import datetime, timezone

from tavily import TavilyClient
from app.graph.errors import RunCancelled, SearchUnavailable
from app.graph.state import AgentState
from app.nodes.queries import parseFeedbackQueries
from app.schemas.models import EvidenceItem
from app.telemetry.collector import currentCollector, emitProgress
from app.telemetry.usage import recordSearch
import os

tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))


def scout_node(state: AgentState) -> dict:
    queries = state["research_plan"]
    feedback = state.get("critique_feedback", "")
    researchRound = state.get("analysis_iteration", 0) + 1

    if feedback:
        queries = parseFeedbackQueries(feedback)

    evidence: list[EvidenceItem] = list(state.get("raw_evidence", []))
    failures: list[str] = []

    for query in queries:
        if currentCollector().isCancelled():
            raise RunCancelled("scout")
        try:
            response = tavily.search(
                query=query,
                max_results=2,
                include_answer=True,
                topic="general",
            )
        except Exception as exc:
            failures.append(type(exc).__name__)
            recordSearch(query, resultCount=0, error=type(exc).__name__)
            emitProgress("evidence", round=researchRound, query=query, status="error", error=type(exc).__name__, items=[])
            continue

        retrievedAt = datetime.now(timezone.utc)
        answer = response.get("answer", "")
        results = response.get("results", [])
        recordSearch(query, resultCount=len(results))

        found: list[EvidenceItem] = []
        for result in results:
            snippet = result.get("content", "")[:800]
            if answer and len(snippet) < 200:
                snippet = f"{snippet} | Summary: {answer[:300]}"

            found.append(
                EvidenceItem(
                    query=query,
                    title=result.get("title", ""),
                    snippet=snippet,
                    source_url=result.get("url", ""),
                    retrieved_at=retrievedAt,
                )
            )
        evidence.extend(found)
        emitProgress(
            "evidence",
            round=researchRound,
            query=query,
            status="ok",
            error=None,
            items=[{"title": item.title, "url": str(item.source_url)} for item in found],
        )

    if queries and len(failures) == len(queries):
        raise SearchUnavailable(f"all {len(queries)} Tavily searches failed ({', '.join(sorted(set(failures)))}).")

    return {"raw_evidence": evidence}
