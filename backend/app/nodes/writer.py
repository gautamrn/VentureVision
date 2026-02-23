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
IMPORTANT: You are scoring the OPPORTUNITY based on what our research agents found — NOT grading the pitch text. The founder wrote an idea. Our agents searched the web and collected evidence. Score based on what that evidence reveals about the market, competition, and opportunity.

Before assigning any score, first identify:
  (a) What does the evidence show about this dimension?
  (b) Does the evidence support or contradict the opportunity?
  (c) How strong/recent/credible is the evidence?

Score anchors (0-100):
  80-100: Strong evidence from multiple credible sources confirms a real opportunity. Rare but possible.
  60-79:  Evidence supports the opportunity — real market, identifiable competitors, viable space.
  40-59:  Mixed signals — some evidence supports it, some contradicts, or evidence is thin.
  20-39:  Evidence mostly contradicts the opportunity, or the space appears saturated/unviable.
  0-19:   Evidence actively disproves the core premise.

If our agents found no evidence for a dimension, cap that subscore at 40 — it means the data is inconclusive, not that the idea is bad.
"""

QUICK_CHECK_PROMPT = """You are a market researcher. A founder came to you with a business idea and asked: "Is this worth building? What does the market look like? Who else is doing this?"

You went out, searched the web, and came back with findings. Now report what you found. You are not grading anything. You are not evaluating a pitch. You are presenting research.

Think of yourself as a smart friend who just spent 30 minutes researching an idea and came back with notes.

You will receive the founder's idea and research evidence collected by a search agent.

OUTPUT FIELDS:

1. pitch_score: 0-100 "opportunity signal" — how much evidence supports this being a real, viable market. This is NOT a grade on the idea or the founder. It measures how much the evidence backs up the opportunity.
   If evidence shows a real market with demand, score 55-75. If evidence shows a large, growing, underserved market, score 75+. If evidence shows the space is oversaturated or the premise doesn't hold up, score below 45. Weighted: market_size 30%, competition 25%, revenue_model 25%, uniqueness 20%.

2. subscores: Rate each 0-100.
   - market_size: Did our research find evidence of a real market? Growing? How big?
   - competition: How crowded is the space? Fewer competitors = higher. But some competition validates the market — that's a good sign, not a penalty.
   - revenue_model: Did our research find evidence of similar businesses making money? If the founder didn't mention pricing, that's fine — score based on whether comparable business models exist in the evidence.
   - uniqueness: Based on what competitors are doing, does this idea approach the problem differently?

3. strengthen_suggestions: 3-5 things worth digging into next. Frame as research leads and next steps: "Look into [Competitor X]'s approach to [problem] — they seem to be doing something similar" or "It might be worth talking to people who use [existing product] to understand what's missing." Each should connect to something from the evidence.

4. executive_summary: 2-3 sentences summarizing your research findings. What does the market look like? Who's already in this space? Where might there be an opening? Write it like you're briefing a friend, not writing a report.

5. market_matrix: Companies you found in the research. ONLY from evidence — do not make up companies.
   - competitor: Company name exactly as found in evidence
   - pricing: Exact figures if found, otherwise "not found in evidence"
   - funding: Exact figures if found, otherwise "not found in evidence"

6. risk_vectors: 3-5 things worth knowing about. Frame as context, not warnings: "There are some well-funded players in this space — [competitor] raised $Xm" or "This market is growing but regulation could be a factor." Landscape observations, not judgments.

7. confidence_score: 0.0-1.0. How much did our research cover? Higher = we found a lot of relevant information. Lower = many unknowns remain.

8. investor_questions: 5-7 questions worth thinking about as you develop this idea. Curious and constructive — things a thoughtful friend would ask.
   - question: The question.
   - why_it_matters: Why this is worth thinking about.

9. pitch_annotations: Look through the founder's ORIGINAL IDEA TEXT and flag interesting parts:
   - excerpt: Exact text (verbatim, short)
   - annotation_type: "strong" | "needs_research"
   - note: For "strong": what our research found that supports this. For "needs_research": what would be worth looking into further. Do not use "weak_claim" or "vague" — this is brainstorming, not a pitch review.
   Include at least 4 annotations. Be generous with "strong" when evidence supports the idea.

10. deal_context: Context on where ideas like this typically sit.
    - typical_stage: e.g. "Early exploration" or "Pre-seed"
    - typical_raise_range: What similar companies raised, based on evidence. If none found, say so.
    - typical_dilution: What's typical at this stage
    - red_flags: 2-3 things to be aware of — framed as helpful context, not warnings

11. feature_suggestions: 3-5 features that competitors offer or that evidence suggests users want. Frame as inspiration: "Competitors like [X] offer [feature] — worth considering for your v1" or "Our research suggests demand for [capability] in this space."

""" + EVIDENCE_RULES

INVESTOR_READY_PROMPT = """You are a venture capital analyst stress-testing a startup opportunity. Your job is to tell the founder exactly what the evidence says — good and bad — so they know what they're walking into before talking to investors.

You are NOT grading the pitch text. The founder described an idea. Our research agents searched the web and collected real evidence. Your job is to analyze what that evidence reveals about the opportunity, the market, and the competition.

Do not use the words: promising, interesting, exciting, great potential, innovative, compelling, notable.

You will receive a startup pitch and research evidence collected by a search agent.

""" + SCORING_CALIBRATION + """

OUTPUT FIELDS:

1. pitch_score: Weighted composite — market_size 30%, competition 25%, revenue_model 25%, uniqueness 20%.
   Score based on what the evidence shows. A decent opportunity with evidence of real market demand should score 45-65. Above 70 = evidence strongly supports the opportunity across multiple dimensions. Above 85 = rare. Below 35 = evidence actively contradicts the core thesis.

2. subscores: Rate each 0-100 using the calibration above.
   - market_size: What does evidence show about market size and growth? Large, growing market with data = score higher. No data found by our agents = cap at 40 (inconclusive).
   - competition: How crowded is the space based on evidence? Few competitors = higher. Well-funded incumbents doing the same thing = lower. But having competitors also validates the market — score accordingly.
   - revenue_model: Does evidence show comparable business models working? If the founder hasn't mentioned pricing, that's fine — score based on whether evidence shows viable revenue models in this space.
   - uniqueness: Based on competitor evidence, how differentiated is this approach? If competitors already do the exact same thing, score lower. If there's a clear gap in the market, score higher.

3. strengthen_suggestions: 3-5 direct, specific actions. "Research [Competitor X]'s pricing model — evidence shows they charge $Y/mo." "Define how you differ from [competitor] — evidence shows they already offer [feature]." Each must reference evidence.

4. executive_summary: 2-3 sentences. What does the evidence say about this opportunity? Where does it support the idea, and where does it raise concerns? Direct, no filler.

5. market_matrix: Competitors found in evidence ONLY. Do not invent companies.
   - competitor: Company name exactly as found in evidence
   - pricing: Exact figures if found, otherwise "not found in evidence"
   - funding: Exact figures if found, otherwise "not found in evidence"

6. risk_vectors: 3-5 blunt risks based on what the evidence revealed. Each must cite a specific finding. "Evidence shows [company] raised $Xm and already offers [feature] — this is a well-funded incumbent in your space." Direct, but grounded in data, not speculation.

7. confidence_score: 0.0-1.0. How much of the opportunity could our agents verify with the evidence collected?

8. investor_questions: 5-8 tough questions a VC would ask, based on gaps or concerns the evidence surfaced.
   - question: The hardball question.
   - why_it_matters: What this question is really testing — reference specific evidence. "Evidence shows [competitor] already does [X], so an investor will want to know your defensible advantage."

9. pitch_annotations: Compare the ORIGINAL PITCH TEXT against the evidence our agents found:
   - excerpt: Exact text from the pitch (verbatim, short)
   - annotation_type: "weak_claim" | "vague" | "unsubstantiated" | "strong"
   - note: What does the evidence say about this claim? "Evidence confirms this — [source] shows [data]" or "Evidence contradicts this — [competitor] already does [X]" or "Our agents found no data to verify this claim." Do NOT criticize the pitch for being short or not including data — that's the agents' job.
   Include at least 5 annotations. Mark claims as "strong" when evidence supports them.

10. deal_context: Data-driven assessment.
    - typical_stage: Based on comparable companies found in evidence
    - typical_raise_range: Based on comparable deals in evidence. If none found, say so.
    - typical_dilution: Typical for the stage
    - red_flags: 2-4 concerns grounded in evidence. "Evidence shows competitors at this stage had [X] — you'll need to demonstrate this to raise."

11. feature_suggestions: 3-5 features that evidence shows are important in this space. "Evidence shows [Competitor X] and [Competitor Y] both offer [feature] — this appears to be table stakes." Each must reference specific evidence.

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
