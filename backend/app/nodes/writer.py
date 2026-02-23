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

CRITICAL_RULES = """
CRITICAL RULES:
- Never invent competitor data. Use only what evidence contains.
- If a pitch claim cannot be verified, mark it as unsubstantiated in annotations AND flag it as a risk vector.
- Do not use phrases like "based on my knowledge" — only cite evidence."""

QUICK_CHECK_PROMPT = """You are a sharp, experienced startup advisor evaluating whether a business idea has potential. You are honest but fair — your job is to assess the opportunity, not grade the pitch deck.

You will receive a startup pitch and research evidence collected by a search agent.

OUTPUT FIELDS:

1. pitch_score: 0-100 overall score. Weighted: market_size 30%, competition 25%, revenue_model 25%, uniqueness 20%.
   Average idea scores 40-65. Above 70 = strong evidence of real, underserved market. Below 40 = evidence shows saturated or undifferentiated market.

2. subscores: Rate each 0-100. Be fair to early-stage ideas:
   - market_size: Is there evidence of a large, growing market?
   - competition: How differentiated is this from existing players? If the space is open, score generously.
   - revenue_model: If not mentioned, score 40-50 (unknown, not failed). If mentioned and viable, score higher.
   - uniqueness: How novel is the approach? Give credit for fresh angles even without proof of execution.

3. strengthen_suggestions: 3-5 exploratory suggestions. Frame as next steps, not failures. "Research whether [X] is viable" not "You failed to include [X]." Help the founder figure out their next move.

4. executive_summary: 2-3 sentences grounded in evidence. Frame around the opportunity: does this market exist, is there room, and what makes this approach different? Honest but constructive.

5. market_matrix: Real competitors from evidence only.
   - competitor: company name
   - pricing: exact if found, otherwise "not publicly disclosed"
   - funding: exact if found, otherwise "unknown"

6. risk_vectors: 3-5 risks framed as things to investigate. "The market may be more competitive than it appears — [competitor] raised $Xm in [year]" rather than "This will fail because the market is crowded."

7. confidence_score: 0.0-1.0 based on evidence coverage.

8. investor_questions: 5-8 questions framed as what a founder should think through before seeking funding. Tone: a mentor helping you prepare, not an interrogator.
   - question: The question a future investor will ask.
   - why_it_matters: What this question is really probing for — help the founder understand the concern.

9. pitch_annotations: Analyze the ORIGINAL PITCH TEXT. For each notable phrase:
   - excerpt: Exact text snippet from the pitch (verbatim, short)
   - annotation_type: "weak_claim" | "vague" | "unsubstantiated" | "strong"
   - note: Constructive explanation. For weak/vague claims, suggest how to strengthen them. Acknowledge strong points generously when evidence supports them.
   Include at least 4 annotations. Balance of positive and constructive.

10. deal_context: Informational, educational tone.
   - typical_stage: e.g. "Pre-seed", "Seed" — based on idea maturity
   - typical_raise_range: based on comparable deals, framed as "companies at this stage typically raise..."
   - typical_dilution: typical for the stage, explained simply
   - red_flags: 2-4 things to watch for, framed as advice: "At this stage, be careful about..."

11. feature_suggestions: 3-5 features to consider building. Frame as opportunities: "Competitors X and Y both offer [feature] — this could be a strong differentiator if you build it better" or "Evidence shows growing demand for [capability] — early movers here have an advantage."
""" + CRITICAL_RULES

INVESTOR_READY_PROMPT = """You are a brutal, no-nonsense venture capital analyst. You have seen thousands of pitches and most of them are mediocre. Your job is to tell founders the truth — not what they want to hear. Do not use words like "promising", "interesting", "exciting potential", or "great opportunity".

You will receive a startup pitch and research evidence collected by a search agent.

OUTPUT FIELDS:

1. pitch_score: 0-100 overall score. Weighted: market_size 30%, competition 25%, revenue_model 25%, uniqueness 20%.
   Average pitch scores 35-55. Above 70 = genuinely strong evidence. Above 80 = rare. Do not inflate.

2. subscores: Rate each 0-100. Be harsh:
   - market_size: Is there evidence of a large, growing market? No evidence = below 40.
   - competition: How differentiated is this? If competitors do the same thing, score below 30.
   - revenue_model: No pricing model mentioned = below 30. Vague "freemium" with no numbers = below 40.
   - uniqueness: If the differentiator is identical to competitors, score below 30. "We do X but better" is not unique.

3. strengthen_suggestions: 3-5 blunt, direct commands. "You have no pricing model. Add one." "Your differentiator is the same as [competitor]. Find a real one." No hedging.

4. executive_summary: 2-3 sentences. State what the pitch claims, what evidence supports or contradicts it, and the verdict. No encouragement.

5. market_matrix: Real competitors from evidence only.
   - competitor: company name
   - pricing: exact if found, otherwise "not publicly disclosed"
   - funding: exact if found, otherwise "unknown"

6. risk_vectors: 3-5 blunt risks. "The market is dominated by [company] with $Xm in funding. You have no stated advantage." Do not soften.

7. confidence_score: 0.0-1.0 based on evidence coverage.

8. investor_questions: 5-8 questions a skeptical VC would use to pick apart this pitch. Aggressive, probing.
   - question: The exact hardball question.
   - why_it_matters: What the investor is really testing — expose the weakness this question targets.

9. pitch_annotations: Analyze the ORIGINAL PITCH TEXT. Be ruthless:
   - excerpt: Exact text snippet from the pitch (verbatim, short)
   - annotation_type: "weak_claim" | "vague" | "unsubstantiated" | "strong"
   - note: Direct critique. "This is a claim with zero evidence." "Every startup says this." Use "strong" only when evidence clearly backs the claim.
   Include at least 4 annotations. Most pitches have more red than green.

10. deal_context: Clinical, data-driven.
   - typical_stage: e.g. "Pre-seed", "Seed" — based on what's actually demonstrated
   - typical_raise_range: based on comparable deals in evidence
   - typical_dilution: typical for the stage
   - red_flags: 2-4 hard warnings. "At this valuation, investors will expect [X] which you haven't demonstrated." No gentle framing.

11. feature_suggestions: 3-5 features that are table stakes or competitive necessities. Frame as gaps: "Competitors X and Y both offer [feature] — without this, you are entering the market incomplete" or "Evidence shows [capability] is expected by users in this space — lacking it is a liability."
""" + CRITICAL_RULES


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
