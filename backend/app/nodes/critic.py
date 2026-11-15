from pydantic import BaseModel
from langchain_openai import ChatOpenAI

from app.graph.state import AgentState
from app.nodes import writer
from app.nodes.queries import parseFeedbackQueries
from app.schemas.models import Citation, EvidenceItem, Groundedness, LlmCall
from app.telemetry.budget import budgetExitReason, configuredBudgetUsd, spentUsd
from app.telemetry.pricing import llmCostUsd, searchCostUsd
from app.telemetry.usage import invokeStructured, structuredOutput

QUICK_MAX_ITERATIONS = 3
DEEP_MAX_ITERATIONS = 4

CITATION_REQUIRED_VERDICTS = {"strong", "contradicted"}
NO_EVIDENCE_VERDICT = {"market_scan": "needs_research", "pitch_lab": "unsubstantiated"}
MIN_QUOTE_WORDS = 3
_EDGE_PUNCTUATION = " .,;:!?\"'()[]…-"
_TYPOGRAPHIC = str.maketrans({"\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"', "\u2013": "-", "\u2014": "-"})


class CritiqueResult(BaseModel):
    is_sufficient: bool
    coverage_score: float
    feedback: str


llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, max_tokens=1024)
critic_llm = structuredOutput(llm, CritiqueResult)

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
    mode = state.get("mode", "market_scan")
    maxIterations = DEEP_MAX_ITERATIONS if mode == "pitch_lab" else QUICK_MAX_ITERATIONS

    if iteration >= maxIterations:
        return {"is_validated": True, "analysis_iteration": iteration}

    plan = state["research_plan"]
    evidence = state.get("raw_evidence", [])
    evidence_text = "\n".join(
        f"- [{e.query}] {e.title}: {e.snippet[:200]}" for e in evidence
    )

    result, call = invokeStructured(
        critic_llm,
        [
            ("system", SYSTEM_PROMPT),
            (
                "human",
                f"Research Plan:\n{chr(10).join(plan)}\n\nEvidence Collected:\n{evidence_text}",
            ),
        ],
    )
    update = {
        "is_validated": result.is_sufficient,
        "critique_feedback": result.feedback,
        "coverage_score": result.coverage_score,
        "analysis_iteration": iteration + 1,
    }
    if not result.is_sufficient:
        reason = budgetStopReason(state, call, result.feedback, completedRounds=iteration + 1)
        if reason:
            update.update(is_validated=True, budget_exit_reason=reason)
    return update


def budgetStopReason(state: AgentState, criticCall: LlmCall, feedback: str, completedRounds: int) -> str | None:
    spentSoFar = spentUsd(state.get("llm_calls", []), state.get("search_calls", [])) + criticCall.cost_usd
    nextRound = searchCostUsd(len(parseFeedbackQueries(feedback))) + criticCall.cost_usd
    writerReserve = llmCostUsd(writer.llm.model_name, 0, writer.llm.max_tokens)
    return budgetExitReason(
        spentSoFarUsd=spentSoFar,
        nextRoundUsd=nextRound,
        writerReserveUsd=writerReserve,
        budgetUsd=state.get("budget_usd", configuredBudgetUsd()),
        completedRounds=completedRounds,
    )


def _normalize(text: str) -> str:
    return " ".join(text.lower().translate(_TYPOGRAPHIC).split())


def isCitationGrounded(citation: Citation | None, evidence: list[EvidenceItem]) -> bool:
    if citation is None:
        return False
    quote = _normalize(citation.quote).strip(_EDGE_PUNCTUATION)
    if len(quote.split()) < MIN_QUOTE_WORDS:
        return False
    return any(
        str(item.source_url) == str(citation.source_url)
        and (quote in _normalize(item.snippet) or quote in _normalize(item.title))
        for item in evidence
    )


def citation_audit_node(state: AgentState) -> dict:
    memo = state.get("final_memo")
    if memo is None:
        return {"final_memo": None}

    evidence = state.get("raw_evidence", [])
    noEvidenceVerdict = NO_EVIDENCE_VERDICT.get(state.get("mode", "market_scan"), "needs_research")
    downgraded = 0

    annotations = []
    for annotation in memo.pitch_annotations:
        citation = annotation.citation if isCitationGrounded(annotation.citation, evidence) else None
        if annotation.annotation_type in CITATION_REQUIRED_VERDICTS and citation is None:
            downgraded += 1
            annotations.append(
                annotation.model_copy(
                    update={
                        "annotation_type": noEvidenceVerdict,
                        "citation": None,
                        "downgraded_from": annotation.annotation_type,
                    }
                )
            )
        else:
            annotations.append(annotation.model_copy(update={"citation": citation}))

    competitors = [
        row.model_copy(update={"citation": row.citation if isCitationGrounded(row.citation, evidence) else None})
        for row in memo.market_matrix
    ]

    claims = [*annotations, *competitors]
    groundedness = Groundedness(
        cited_claims=sum(1 for claim in claims if claim.citation is not None),
        total_claims=len(claims),
        downgraded_claims=downgraded,
    )

    return {
        "final_memo": memo.model_copy(
            update={
                "pitch_annotations": annotations,
                "market_matrix": competitors,
                "groundedness": groundedness,
            }
        )
    }
