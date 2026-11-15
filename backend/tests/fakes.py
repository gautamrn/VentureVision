import json
import re
from typing import Any

import httpx
from langchain_openai import ChatOpenAI

SAMPLE_PITCH = (
    "An on-demand dog walking marketplace that matches busy urban pet owners "
    "with vetted local walkers, charging a 20% commission per walk."
)


class FakeOpenAI:
    """Stands in for the OpenAI HTTP API.

    Responses are scripted per structured-output schema name (ResearchPlan,
    CritiqueResult, MemoSynthesis). Each request consumes the next scripted
    reply; the last reply repeats once the script runs out.
    """

    def __init__(self) -> None:
        self.scripts: dict[str, list[Any]] = {}
        self.calls: list[dict] = []
        self.unscripted: list[str] = []
        self.usage = {"prompt_tokens": 1, "completion_tokens": 1}

    def script(self, schemaName: str, *replies: Any) -> None:
        self.scripts[schemaName] = list(replies)

    def callsFor(self, schemaName: str) -> list[dict]:
        return [c for c in self.calls if c["schema"] == schemaName]

    def chatModel(self) -> ChatOpenAI:
        return ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,
            api_key="test-openai-key",
            max_retries=0,
            http_client=httpx.Client(transport=httpx.MockTransport(self._handle)),
        )

    def _handle(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        schemaName = _schemaNameOf(body)
        self.calls.append({"schema": schemaName, "messages": body["messages"], "body": body})

        queue = self.scripts.get(schemaName)
        if not queue:
            self.unscripted.append(schemaName)
            return httpx.Response(500, json={"error": {"message": f"unscripted {schemaName}"}})

        reply = queue.pop(0) if len(queue) > 1 else queue[0]
        content = reply if isinstance(reply, str) else json.dumps(reply)

        if "tools" in body:
            message = {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_test",
                        "type": "function",
                        "function": {"name": schemaName, "arguments": content},
                    }
                ],
            }
        else:
            message = {"role": "assistant", "content": content, "refusal": None}

        return httpx.Response(
            200,
            json={
                "id": "chatcmpl-test",
                "object": "chat.completion",
                "created": 0,
                "model": "gpt-4o-mini",
                "choices": [
                    {"index": 0, "message": message, "finish_reason": "stop", "logprobs": None}
                ],
                "usage": {**self.usage, "total_tokens": sum(self.usage.values())},
            },
        )


def _schemaNameOf(body: dict) -> str:
    responseFormat = body.get("response_format") or {}
    if responseFormat.get("type") == "json_schema":
        return responseFormat["json_schema"]["name"]
    if body.get("tools"):
        return body["tools"][0]["function"]["name"]
    return "<unstructured>"


class FakeTavily:
    """Stands in for TavilyClient. Returns one result per query unless told otherwise."""

    def __init__(self) -> None:
        self.queries: list[str] = []
        self.emptyQueries: set[str] = set()

    def search(self, query: str, **kwargs: Any) -> dict:
        self.queries.append(query)
        if query in self.emptyQueries:
            return {"answer": "", "results": []}

        slug = re.sub(r"[^a-z0-9]+", "-", query.lower()).strip("-")
        return {
            "answer": f"Summary for {query}",
            "results": [
                {
                    "title": f"Result for {query}",
                    "url": f"https://example.com/{slug}",
                    "content": f"Evidence about {query}. " * 10,
                }
            ],
        }


def runGraph(
    pitch: str = SAMPLE_PITCH, mode: str = "market_scan", budgetUsd: float | None = None
) -> tuple[list[str], dict]:
    """Runs the real compiled graph; returns the node visit order and the final state."""
    from app.graph.workflow import ventureGraph
    from app.routers.analyze import buildInitialState

    order: list[str] = []
    finalState: dict = {}
    for streamMode, chunk in ventureGraph.stream(
        buildInitialState(pitch, mode, budgetUsd), stream_mode=["updates", "values"]
    ):
        if streamMode == "updates":
            order.extend(chunk.keys())
        else:
            finalState = chunk
    return order, finalState


def researchPlan(queries: list[str]) -> dict:
    return {"queries": queries}


def critique(coverageScore: float, isSufficient: bool, feedback: str = "") -> dict:
    return {"is_sufficient": isSufficient, "coverage_score": coverageScore, "feedback": feedback}


def annotationDraft(
    annotationType: str,
    excerpt: str = "vetted local walkers",
    evidenceRef: int | None = None,
    evidenceQuote: str | None = None,
) -> dict:
    return {
        "excerpt": excerpt,
        "annotation_type": annotationType,
        "note": f"{annotationType} note",
        "evidence_ref": evidenceRef,
        "evidence_quote": evidenceQuote,
    }


def competitorDraft(
    competitor: str = "Rover", evidenceRef: int | None = None, evidenceQuote: str | None = None
) -> dict:
    return {
        "competitor": competitor,
        "pricing": "not found in evidence",
        "funding": "$310M",
        "evidence_ref": evidenceRef,
        "evidence_quote": evidenceQuote,
    }


def memoSynthesis(
    pitchScore: int = 64,
    annotations: list[dict] | None = None,
    competitors: list[dict] | None = None,
) -> dict:
    return {
        "pitch_score": pitchScore,
        "subscores": {"market_size": 70, "competition": 55, "revenue_model": 62, "uniqueness": 48},
        "strengthen_suggestions": ["Look into Rover's walker vetting process."],
        "executive_summary": "Evidence shows an established market with funded incumbents.",
        "market_matrix": competitors if competitors is not None else [competitorDraft()],
        "risk_vectors": ["Well-funded incumbents dominate urban markets."],
        "confidence_score": 0.7,
        "investor_questions": [
            {"question": "How do you acquire walkers?", "why_it_matters": "Supply drives liquidity."}
        ],
        "pitch_annotations": (
            annotations if annotations is not None else [annotationDraft("needs_research")]
        ),
        "deal_context": {
            "typical_stage": "Pre-seed",
            "typical_raise_range": "not found in evidence",
            "typical_dilution": "10-20%",
            "red_flags": ["Low switching costs for owners."],
        },
        "feature_suggestions": ["GPS walk tracking, as offered by competitors."],
    }
