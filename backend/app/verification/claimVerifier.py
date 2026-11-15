from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from app.schemas.evals import EvalLabel, EvidenceSnippet
from app.telemetry.usage import invokeStructured, structuredOutput
from app.verification.grounding import quoteAppearsIn

QUOTE_REQUIRED_LABELS: set[EvalLabel] = {"supported", "contradicted"}


class ClaimVerdictDraft(BaseModel):
    verdict: EvalLabel
    evidence_ref: int | None
    evidence_quote: str | None
    reasoning: str


class VerifiedQuote(BaseModel):
    evidence_index: int
    quote: str
    source_url: str | None


class ClaimVerification(BaseModel):
    verdict: EvalLabel
    reasoning: str
    citation: VerifiedQuote | None
    downgraded_from: EvalLabel | None
    model: str
    cost_usd: float


llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, max_tokens=512)
verifier_llm = structuredOutput(llm, ClaimVerdictDraft)

SYSTEM_PROMPT = """You are a claim verifier for a due diligence system. You receive one claim and numbered evidence items [E1], [E2], ... Judge the claim ONLY against that evidence. Never use outside knowledge.

VERDICT BOUNDARY:
- "supported": an evidence item states the same fact, or a figure consistent with the claim.
- "contradicted": an evidence item states the OPPOSITE fact, or a number that cannot be true at the same time as the claim, about the SAME subject (same metric, market, and period).
- "unsupported": no evidence item addresses the claim, or the evidence concerns a different subject, scope, unit, or period, or it is thin or ambiguous.
THE BOUNDARY: absence of evidence is never "contradicted". If you cannot quote one sentence from the evidence that is incompatible with the claim, the verdict is "unsupported", not "contradicted".

CITATION:
- "supported" and "contradicted" MUST cite: evidence_ref is the item number (3 for [E3]) and evidence_quote is text copied VERBATIM from that item. Quotes are checked automatically; a missing or altered quote turns the verdict into "unsupported".
- "unsupported": evidence_ref and evidence_quote are null.

reasoning: one or two sentences naming the specific fact or number that decided the verdict."""


def formatEvidence(evidence: list[EvidenceSnippet]) -> str:
    if not evidence:
        return "(no evidence items)"
    return "\n\n".join(
        f"[E{i}] Source: {item.source_url or 'not given'}\nTitle: {item.title}\nContent: {item.text}"
        for i, item in enumerate(evidence, start=1)
    )


def groundedQuote(draft: ClaimVerdictDraft, evidence: list[EvidenceSnippet]) -> VerifiedQuote | None:
    if draft.evidence_ref is None or not draft.evidence_quote or not 1 <= draft.evidence_ref <= len(evidence):
        return None
    item = evidence[draft.evidence_ref - 1]
    if not quoteAppearsIn(draft.evidence_quote, (item.text, item.title)):
        return None
    return VerifiedQuote(evidence_index=draft.evidence_ref, quote=draft.evidence_quote.strip(), source_url=item.source_url)


def verifyClaim(claim: str, evidence: list[EvidenceSnippet]) -> ClaimVerification:
    draft, call = invokeStructured(
        verifier_llm,
        [("system", SYSTEM_PROMPT), ("human", f"Claim:\n{claim}\n\nEvidence:\n{formatEvidence(evidence)}")],
    )
    citation = groundedQuote(draft, evidence)
    verdict, downgradedFrom = draft.verdict, None
    if verdict in QUOTE_REQUIRED_LABELS and citation is None:
        verdict, downgradedFrom = "unsupported", draft.verdict
    return ClaimVerification(
        verdict=verdict,
        reasoning=draft.reasoning,
        citation=citation if verdict in QUOTE_REQUIRED_LABELS else None,
        downgraded_from=downgradedFrom,
        model=call.model,
        cost_usd=call.cost_usd,
    )
