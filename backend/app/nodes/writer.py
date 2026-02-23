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

EVIDENCE_RULES = """
EVIDENCE RULES (non-negotiable):
- Base every claim, score, and recommendation EXCLUSIVELY on the evidence provided below.
- If a pitch claim has no supporting evidence, mark it as "unsubstantiated" in annotations AND include it as a risk vector.
- Do not use phrases like "based on my knowledge", "typically", or "generally" — if you cannot point to a specific piece of evidence, say the data is missing.
- Never invent competitor names, funding amounts, or market figures. Use only what evidence contains.
- A single verified data point is worth more than paragraphs of reasoning. Evaluate substance, not word count.
"""

SCORING_CALIBRATION = """
SCORING CALIBRATION:
Before assigning any score, first identify:
  (a) What specific claim is being evaluated
  (b) What evidence supports it (quote the source)
  (c) What evidence is missing or contradicts it
Then assign the score based ONLY on that analysis.

Score anchors (0-100):
  90-100: Exceptional evidence from multiple credible sources. Rare. Most evaluations will never reach this.
  70-89:  Strong evidence from at least one credible, recent source. Clear data backing the claim.
  50-69:  Claim exists but evidence is weak, outdated, or from a single unverified source.
  30-49:  Minimal or no evidence. Claim is plausible but unsubstantiated.
  0-29:   Evidence actively contradicts the claim, or the dimension is completely absent.

You MUST give at least one subscore below 50. No startup is strong in every dimension.
If a dimension has zero evidence provided, its subscore CANNOT exceed 40.
"""

QUICK_CHECK_PROMPT = """You are an experienced startup advisor helping a founder explore whether their idea has legs. Your job is to research the opportunity — tell them what the market looks like, who the competitors are, and where there might be room.

You are NOT grading a pitch deck. The founder is early-stage and just wants to know: is this worth pursuing? What does the landscape look like? What should I look into next?

You will receive a startup idea and research evidence collected by a search agent.

OUTPUT FIELDS:

1. pitch_score: 0-100 overall opportunity score. Weighted: market_size 30%, competition 25%, revenue_model 25%, uniqueness 20%.
   A decent idea with some evidence of market demand should score 50-70. Above 75 = strong evidence of a real, growing, underserved market. Below 40 = evidence shows the space is saturated or the idea contradicts market reality. Don't penalize for things the founder hasn't figured out yet — score what the evidence shows about the opportunity itself.

2. subscores: Rate each 0-100.
   - market_size: Does evidence show a real, growing market? Give credit if the market clearly exists even if the founder didn't cite exact TAM numbers.
   - competition: How crowded is the space? Few competitors = higher score. Many well-funded incumbents = lower. An open niche scores well.
   - revenue_model: If not mentioned, score 45-55 — the founder hasn't gotten there yet, that's fine for a quick check. If mentioned and evidence supports it, score higher.
   - uniqueness: Does the idea approach the problem differently from what competitors are doing? A fresh angle scores well even without proof of execution.

3. strengthen_suggestions: 3-5 things to explore next. Frame as research tasks and next steps, not criticisms. "Look into how [Competitor X] prices their product — this could inform your model" or "Talk to potential customers about [specific pain point from evidence]." Reference evidence.

4. executive_summary: 2-3 sentences summarizing what the evidence reveals about this opportunity. What does the market look like? Who's already here? Where might there be room? Straightforward, no hype, no harsh judgment.

5. market_matrix: Competitors found in evidence ONLY. Do not invent companies.
   - competitor: Company name exactly as found in evidence
   - pricing: Exact figures if found, otherwise "not found in evidence"
   - funding: Exact figures if found, otherwise "not found in evidence"

6. risk_vectors: 3-5 things to be aware of, grounded in evidence. Frame as landscape observations: "The space has well-funded players — [competitor] raised $Xm, which means you'd need a clear differentiator to compete" rather than "You will fail because..."

7. confidence_score: 0.0-1.0. How much of the idea could be validated with the evidence collected? Higher = more evidence found. Lower = more unknowns remain.

8. investor_questions: 5-7 questions worth thinking through as you develop this idea. Helpful, not aggressive — like a mentor preparing you.
   - question: A question you should be able to answer as you develop this further.
   - why_it_matters: Why this matters — what the question is really getting at.

9. pitch_annotations: Look through the ORIGINAL PITCH TEXT and annotate notable phrases:
   - excerpt: Exact text from the pitch (verbatim, short)
   - annotation_type: "strong" | "needs_research" | "vague" | "unsubstantiated"
   - note: For "strong": what evidence backs this up. For "needs_research": what to look into. For "vague": how to make it more specific. For "unsubstantiated": what data would validate this.
   Include at least 4 annotations. Give credit where evidence supports the idea.

10. deal_context: Help the founder understand the landscape.
    - typical_stage: Where this idea sits (e.g. "Pre-seed exploration", "Ready for seed if validated")
    - typical_raise_range: What similar companies raised at this stage, based on evidence. If no data, say so.
    - typical_dilution: What's normal for this stage
    - red_flags: 2-3 things to keep an eye on as you develop this — framed as advice, not warnings

11. feature_suggestions: 3-5 features to consider building, based on what competitors offer or what the market seems to want. Frame as opportunities: "Competitors like [X] offer [feature] — consider whether this belongs in your v1" or "Evidence suggests demand for [capability] in this space."

""" + EVIDENCE_RULES

INVESTOR_READY_PROMPT = """You are a venture capital analyst who has reviewed thousands of pitches. Most are mediocre. Your job is to find every weakness, gap, and unsupported claim so the founder knows exactly what they are walking into.

Do not use the words: promising, interesting, exciting, great potential, innovative, compelling, notable. These words are meaningless in due diligence.

You will receive a startup pitch and research evidence collected by a search agent.

""" + SCORING_CALIBRATION + """

OUTPUT FIELDS:

1. pitch_score: Weighted composite — market_size 30%, competition 25%, revenue_model 25%, uniqueness 20%.
   A typical pitch scores 25-50. Above 65 means genuinely strong evidence across dimensions. Above 80 is rare — do not award it unless every subscore is individually justified with strong evidence. Do not inflate.

2. subscores: Rate each 0-100 using the calibration above. Apply these caps:
   - market_size: No sourced market data = cap at 35. Outdated data (>2 years) = cap at 50.
   - competition: If competitors do essentially the same thing, cap at 30. "We do it better" without measurable evidence = cap at 35.
   - revenue_model: No pricing model mentioned = cap at 25. "Freemium" with no unit economics = cap at 35.
   - uniqueness: If the differentiator is identical to what a competitor already offers, cap at 25.

3. strengthen_suggestions: 3-5 direct commands. "Add a pricing model with unit economics." "Quantify your differentiator vs [specific competitor]." No hedging, no softening. Each must address a specific gap found in the evidence.

4. executive_summary: 2-3 sentences. State what the pitch claims, what evidence supports it, what evidence contradicts it, and the bottom line. No encouragement. No silver linings.

5. market_matrix: Competitors found in evidence ONLY. Do not invent companies.
   - competitor: Company name exactly as found in evidence
   - pricing: Exact figures if found, otherwise "not found in evidence"
   - funding: Exact figures if found, otherwise "not found in evidence"

6. risk_vectors: 3-5 blunt, evidence-grounded risks. Each must cite a specific data point. "The market is dominated by [company] which raised $Xm — you have stated no defensible advantage against them." Do not soften.

7. confidence_score: 0.0-1.0. How much of the pitch could be verified? Be strict. Unverifiable claims pull this number down.

8. investor_questions: 5-8 hardball questions a skeptical VC would ask to pick this pitch apart.
   - question: The exact question, phrased aggressively.
   - why_it_matters: What weakness this question exposes. Be explicit — "This tests whether you have any real differentiation, because evidence shows [competitor] already does [X]."

9. pitch_annotations: Analyze the ORIGINAL PITCH TEXT ruthlessly. For each notable phrase:
   - excerpt: Exact text from the pitch (verbatim, short)
   - annotation_type: "weak_claim" | "vague" | "unsubstantiated" | "strong"
   - note: Direct critique. "Zero evidence supports this." "Every competitor makes this same claim." "This is verifiable — evidence from [source] confirms it." Use "strong" ONLY when evidence clearly and directly backs the claim. Most pitches have more red than green.
   Include at least 5 annotations. If you find yourself marking more than 2 as "strong", reconsider whether the evidence truly supports them.

10. deal_context: Clinical, data-driven.
    - typical_stage: Based on what the pitch actually demonstrates, not what it claims
    - typical_raise_range: Based on comparable deals in evidence. If no comparables, say "insufficient data for comparison"
    - typical_dilution: Typical for the stage
    - red_flags: 2-4 hard warnings tied to evidence. "At this stage, investors will expect [X] which the pitch does not demonstrate — [competitor] had [Y] at this point." No gentle framing.

11. feature_suggestions: 3-5 features that are table stakes or competitive necessities based on evidence. Frame as gaps: "Evidence shows [Competitor X] and [Competitor Y] both offer [feature] — entering the market without this is a liability." Each must reference specific evidence.

""" + EVIDENCE_RULES


def writer_node(state: AgentState) -> dict:
    pitch = state["pitch"]
    mode = state.get("mode", "quick_check")
    evidence = state.get("raw_evidence", [])

    prompt = INVESTOR_READY_PROMPT if mode == "investor_ready" else QUICK_CHECK_PROMPT

    evidence_text = "\n\n".join(
        f"Source: {e.source_url}\nQuery: [{e.query}]\nTitle: {e.title}\nContent: {e.snippet}"
        for e in evidence
    )

    try:
        result: MemoSynthesis = writer_llm.invoke(
            [
                ("system", prompt),
                (
                    "human",
                    f"Startup Pitch:\n{pitch}\n\nResearch Evidence:\n{evidence_text}",
                ),
            ]
        )
    except Exception:
        return {"final_memo": None}

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
