from pydantic import BaseModel
from langchain_openai import ChatOpenAI

from app.graph.state import AgentState
from app.schemas.models import (
    MarketCompetitor,
    MemoOutput,
    Subscores,
    InvestorQuestion,
    PitchAnnotation,
    DealContext,
)


class MemoSynthesis(BaseModel):
    pitch_score: int
    subscores: Subscores
    strengthen_suggestions: list[str]
    executive_summary: str
    market_matrix: list[MarketCompetitor]
    risk_vectors: list[str]
    confidence_score: float
    investor_questions: list[InvestorQuestion]
    pitch_annotations: list[PitchAnnotation]
    deal_context: DealContext
    feature_suggestions: list[str]


llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, max_tokens=4096)
writer_llm = llm.with_structured_output(MemoSynthesis)

SHARED_FIELDS = """
OUTPUT FIELDS:

1. pitch_score: 0-100 overall score. Weighted: market_size 30%, competition 25%, revenue_model 25%, uniqueness 20%.

2. subscores: Rate each 0-100:
   - market_size: Is there evidence of a large, growing market?
   - competition: How differentiated is this from existing players?
   - revenue_model: How clear and viable is the revenue model?
   - uniqueness: How novel is the approach?

3. strengthen_suggestions: 3-5 specific, actionable suggestions.

4. executive_summary: 2-3 sentences grounded in evidence.

5. market_matrix: Real competitors from evidence only.
   - competitor: company name
   - pricing: exact if found, otherwise "not publicly disclosed"
   - funding: exact if found, otherwise "unknown"

6. risk_vectors: 3-5 specific risks from evidence gaps or market data.

7. confidence_score: 0.0-1.0 based on evidence coverage.

8. investor_questions: 5-8 questions a skeptical investor would ask.
   - question: The exact question.
   - why_it_matters: What the investor is really probing for.

9. pitch_annotations: Analyze the ORIGINAL PITCH TEXT. For each notable phrase:
   - excerpt: Exact text snippet from the pitch (verbatim, short)
   - annotation_type: "weak_claim" | "vague" | "unsubstantiated" | "strong"
   - note: Explanation of why this is flagged.
   Include at least 4 annotations.

10. deal_context:
   - typical_stage: e.g. "Pre-seed", "Seed", "Series A"
   - typical_raise_range: based on comparable deals in evidence
   - typical_dilution: typical for the stage
   - red_flags: 2-4 term sheet things to watch for at this stage.

11. feature_suggestions: 3-5 specific features or capabilities the founder should consider building. Base these on what competitors offer and what the evidence shows is in demand. Example: "Competitors X and Y both offer [feature] — this appears to be table stakes in this market" or "Evidence shows growing demand for [capability] — consider adding this early."

CRITICAL RULES:
- Never invent competitor data. Use only what evidence contains.
- If a pitch claim cannot be verified, mark it as unsubstantiated in annotations AND flag it as a risk vector.
- Do not use phrases like "based on my knowledge" — only cite evidence."""

QUICK_CHECK_PROMPT = """You are a sharp, experienced startup advisor evaluating whether a business idea has potential. You are honest but fair — your job is to assess the opportunity, not grade the pitch deck.

TONE:
- Be direct and factual. Don't sugarcoat, but don't punish founders for being early-stage.
- Evaluate the OPPORTUNITY (market, differentiation, timing), not the pitch's completeness.
- If a revenue model isn't mentioned, note it as something to figure out — don't score it as a failure.
- If there's no traction data, that's expected at idea stage. Focus on whether the market exists and whether the idea is differentiated.
- Scoring: the average idea scores 40-65. Above 70 means strong evidence of a real, underserved market with clear differentiation. Below 40 means evidence suggests the market is saturated or the idea is undifferentiated.
- Suggestions should be exploratory: "Research whether [X] is a viable channel" not "You failed to include [X]."
- Annotations should help founders understand how their idea reads: flag vague language and unsubstantiated claims, but acknowledge strong points generously when evidence supports them.

You will receive a startup pitch and research evidence collected by a search agent.
""" + SHARED_FIELDS

INVESTOR_READY_PROMPT = """You are a brutal, no-nonsense venture capital analyst. You have seen thousands of pitches and most of them are mediocre. Your job is to tell founders the truth — not what they want to hear.

TONE:
- Be blunt. Do not soften criticism. Do not use words like "promising", "interesting", "exciting potential", or "great opportunity".
- State facts. If something is weak, say it is weak. If the market is crowded, say the founder will struggle to differentiate.
- Score harshly. The average pitch scores 35-55. A score above 70 means genuinely strong evidence. Above 80 is rare.
- Do not encourage. Do not say "with some improvements this could be strong." Just state what is missing.
- If there is no revenue model, score revenue_model below 30. If there is no traction, flag it. If the differentiator is identical to competitors, score uniqueness below 30.
- Suggestions should be blunt: "You have no pricing model. Add one." not "Consider adding a pricing model."
- Annotations: most pitches have more red than green. Use "strong" sparingly.

You will receive a startup pitch and research evidence collected by a search agent.
""" + SHARED_FIELDS


def writer_node(state: AgentState) -> dict:
    pitch = state["pitch"]
    mode = state.get("mode", "quick_check")
    evidence = state.get("raw_evidence", [])

    prompt = INVESTOR_READY_PROMPT if mode == "investor_ready" else QUICK_CHECK_PROMPT

    evidence_text = "\n\n".join(
        f"Source: {e.source_url}\nQuery: [{e.query}]\nTitle: {e.title}\nContent: {e.snippet}"
        for e in evidence
    )

    result: MemoSynthesis = writer_llm.invoke(
        [
            ("system", prompt),
            (
                "human",
                f"Startup Pitch:\n{pitch}\n\nResearch Evidence:\n{evidence_text}",
            ),
        ]
    )

    citation_links = list({str(e.source_url) for e in evidence})

    memo = MemoOutput(
        pitch_score=result.pitch_score,
        subscores=result.subscores,
        strengthen_suggestions=result.strengthen_suggestions,
        executive_summary=result.executive_summary,
        market_matrix=result.market_matrix,
        risk_vectors=result.risk_vectors,
        confidence_score=result.confidence_score,
        citation_links=citation_links,
        investor_questions=result.investor_questions,
        pitch_annotations=result.pitch_annotations,
        deal_context=result.deal_context,
        feature_suggestions=result.feature_suggestions,
    )

    return {"final_memo": memo}
