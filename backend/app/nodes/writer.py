from pydantic import BaseModel
from langchain_openai import ChatOpenAI

from app.graph.state import AgentState
from app.schemas.models import (
    AnnotationType,
    Citation,
    EvidenceItem,
    MarketCompetitor,
    MemoOutput,
    Subscores,
    InvestorQuestion,
    PitchAnnotation,
    DealContext,
)
from app.telemetry.usage import invokeStructured, structuredOutput


class AnnotationDraft(BaseModel):
    excerpt: str
    annotation_type: AnnotationType
    note: str
    evidence_ref: int | None
    evidence_quote: str | None


class CompetitorDraft(BaseModel):
    competitor: str
    pricing: str
    funding: str
    evidence_ref: int | None
    evidence_quote: str | None


class MemoSynthesis(BaseModel):
    pitch_score: int
    subscores: Subscores
    strengthen_suggestions: list[str]
    executive_summary: str
    market_matrix: list[CompetitorDraft]
    risk_vectors: list[str]
    confidence_score: float
    investor_questions: list[InvestorQuestion]
    pitch_annotations: list[AnnotationDraft]
    deal_context: DealContext
    feature_suggestions: list[str]


llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, max_tokens=4096)
writer_llm = structuredOutput(llm, MemoSynthesis)

EVIDENCE_RULES = """
EVIDENCE RULES (non-negotiable):
- Base every claim, score, and recommendation EXCLUSIVELY on the evidence provided below.
- If a pitch claim has no supporting evidence, give it this mode's no-evidence verdict in annotations AND include it as a risk vector.
- Do not use phrases like "based on my knowledge", "typically", or "generally" — if you cannot point to a specific piece of evidence, say the data is missing.
- Never invent competitor names, funding amounts, or market figures. Use only what evidence contains.
- A single verified data point is worth more than paragraphs of reasoning. Evaluate substance, not word count.
"""


def verdictRules(noEvidenceVerdict: str) -> str:
    return f"""
VERDICT BOUNDARY (every pitch annotation):
- "strong": an evidence item states the same fact, or a figure consistent with the claim.
- "contradicted": an evidence item states the OPPOSITE fact, or a number that cannot be true at the same time as the claim, about the SAME subject (same metric, market, and period). Examples: the pitch says "no direct competitors" and evidence names a funded competitor doing the same thing; the pitch says "$50B market" and evidence says the same market is $4B.
- "{noEvidenceVerdict}": no evidence item addresses the claim, or the evidence concerns a different subject, scope, or period, or it is thin or ambiguous.
THE BOUNDARY: absence of evidence is never "contradicted". If you cannot quote one sentence from the evidence that is incompatible with the claim, the verdict is "{noEvidenceVerdict}", not "contradicted".

CITATIONS:
- Evidence items are numbered [E1], [E2], ... Every pitch annotation and every market_matrix row has evidence_ref (the item number: 3 for [E3]) and evidence_quote (one sentence copied VERBATIM from that item's Content).
- "strong" and "contradicted" annotations MUST cite. Citations are verified against the evidence automatically; an uncited or misquoted "strong" or "contradicted" annotation is downgraded to "{noEvidenceVerdict}".
- "{noEvidenceVerdict}" and "vague" annotations: set evidence_ref and evidence_quote to null.
- market_matrix rows: cite the item that names the competitor (and its pricing or funding, if given); null if none.
- Never paraphrase, merge sentences, or invent a quote.
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
   - evidence_ref, evidence_quote: see CITATIONS

6. risk_vectors: 3-5 things worth knowing about. Frame as context, not warnings: "There are some well-funded players in this space — [competitor] raised $Xm" or "This market is growing but regulation could be a factor." Landscape observations, not judgments.

7. confidence_score: 0.0-1.0. How much did our research cover? Higher = we found a lot of relevant information. Lower = many unknowns remain.

8. investor_questions: 5-7 questions worth thinking about as you develop this idea. Curious and constructive — things a thoughtful friend would ask.
   - question: The question.
   - why_it_matters: Why this is worth thinking about.

9. pitch_annotations: Look through the founder's ORIGINAL IDEA TEXT and flag interesting parts:
   - excerpt: Exact text (verbatim, short)
   - annotation_type: "strong" | "contradicted" | "needs_research" (see VERDICT BOUNDARY)
   - note: For "strong": what our research found that supports this. For "contradicted": what the evidence says instead. For "needs_research": what would be worth looking into further. Do not use "weak_claim", "vague", or "unsubstantiated" — this is brainstorming, not a pitch review.
   - evidence_ref, evidence_quote: see CITATIONS
   Include at least 4 annotations. Use "strong" whenever evidence supports the idea.

10. deal_context: Context on where ideas like this typically sit.
    - typical_stage: e.g. "Early exploration" or "Pre-seed"
    - typical_raise_range: What similar companies raised, based on evidence. If none found, say so.
    - typical_dilution: What's typical at this stage
    - red_flags: 2-3 things to be aware of — framed as helpful context, not warnings

11. feature_suggestions: 3-5 features that competitors offer or that evidence suggests users want. Frame as inspiration: "Competitors like [X] offer [feature] — worth considering for your v1" or "Our research suggests demand for [capability] in this space."

""" + EVIDENCE_RULES + verdictRules("needs_research")

PITCH_LAB_CALIBRATION = """
PITCH READINESS SCORING:
You are scoring how INVESTOR-READY this pitch is — not the idea itself. A great idea with a vague, unsupported pitch scores low. A decent idea with a specific, evidence-backed pitch scores high.

Before assigning any score, evaluate:
  (a) Does the pitch make specific, verifiable claims?
  (b) Does the evidence our agents found support or contradict those claims?
  (c) Does the pitch address the competitive landscape, market size, and business model?

Score anchors (0-100):
  70-100: Pitch is specific, evidence-backed, and addresses key dimensions. Ready for investor conversations.
  50-69:  Pitch has a real opportunity but needs sharpening — vague claims, missing data points, or gaps an investor would notice.
  30-49:  Pitch needs significant work — key claims are unsupported, competitors aren't addressed, or the business model is unclear.
  0-29:   Pitch is too vague to evaluate, or evidence actively contradicts core claims.

If the pitch doesn't mention a dimension (e.g., no pricing model), that's a gap to flag — not a reason to assume the worst. Score based on what IS there, and annotate what's MISSING.
"""

PITCH_LAB_PROMPT = """You are a pitch coach. A founder wrote a startup pitch. Our research agents went out, searched the web, and collected real market evidence. Your job: use that evidence to make their pitch stronger.

You are NOT judging whether this is a good idea. You are helping the founder say it better — with data, specificity, and awareness of the competitive landscape. Think of yourself as a sharp friend who reads the pitch and says "here's how to make this land with investors."

Do not use the words: promising, interesting, exciting, great potential, innovative, compelling, notable.

You will receive a startup pitch and research evidence collected by a search agent.

""" + PITCH_LAB_CALIBRATION + """

OUTPUT FIELDS:

1. pitch_score: "Pitch Readiness Score" 0-100. How investor-ready is this pitch as written, given what the evidence shows? Weighted: market_size 30%, competition 25%, revenue_model 25%, uniqueness 20%.

2. subscores: Rate each 0-100 based on how well the PITCH addresses each dimension, using evidence as the benchmark.
   - market_size: Does the pitch make strong, evidence-backed market claims? If the pitch says "huge market" but doesn't cite numbers, and our evidence found specific figures — that's a gap. Score based on how well the pitch captures what the evidence shows.
   - competition: Does the pitch clearly differentiate from competitors found in evidence? If evidence shows 5 funded competitors and the pitch doesn't mention any, score low. If the pitch names competitors and explains the difference, score high.
   - revenue_model: Is the revenue approach clear and supported by comparable models in evidence? A pitch that says "we'll monetize later" scores lower than one referencing pricing models evidence shows are working.
   - uniqueness: Does the pitch articulate what's different? If evidence shows competitors already do the exact same thing and the pitch doesn't address why this is different, score low.

3. strengthen_suggestions: 3-5 specific ways to sharpen this pitch. Each must reference evidence and suggest a concrete change:
   - "Add the market size figure — evidence shows this market is $Xbn by 2025. Saying 'large market' is vague; '$Xbn market growing at Y%' is fundable."
   - "Name your top 2 competitors and explain your edge — evidence shows [X] and [Y] are in this space. Investors will already know them."
   - "Add a revenue model reference — evidence shows [competitor] charges $X/mo. Position your pricing against theirs."

4. executive_summary: 2-3 sentences. What does this pitch do well, and where does it need work? Direct assessment of the pitch text against the evidence. "Your pitch clearly identifies the problem, but doesn't address the competitive landscape — evidence shows [X] and [Y] are well-funded in this space."

5. market_matrix: Competitors found in evidence ONLY. Do not invent companies. This data is for the founder to reference in their next pitch draft.
   - competitor: Company name exactly as found in evidence
   - pricing: Exact figures if found, otherwise "not found in evidence"
   - funding: Exact figures if found, otherwise "not found in evidence"
   - evidence_ref, evidence_quote: see CITATIONS

6. risk_vectors: 3-5 gaps in the pitch that evidence exposes. Frame as "your pitch doesn't address this, but an investor will notice":
   - "Evidence shows [competitor] raised $Xm — your pitch doesn't mention how you compete with well-funded players. Add a differentiation statement."
   - "Evidence shows regulatory concerns in this space — your pitch should acknowledge this and explain your compliance approach."
   Each gap should include what the founder can do about it.

7. confidence_score: 0.0-1.0. How much of the pitch could our agents verify with the evidence collected?

8. investor_questions: 5-8 questions that a reader of this pitch would immediately ask. Frame as "your pitch should answer this":
   - question: The question an investor will ask after reading this pitch.
   - why_it_matters: What's missing from the pitch that triggers this question. "Your pitch claims [X] but doesn't back it up — an investor will want to see the data."

9. pitch_annotations: THE MAIN DELIVERABLE. Walk through the founder's ORIGINAL PITCH TEXT and annotate it:
   - excerpt: Exact text from the pitch (verbatim, short phrase or sentence)
   - annotation_type: "strong" | "contradicted" | "weak_claim" | "vague" | "unsubstantiated" (see VERDICT BOUNDARY)
   - note: Specific, actionable feedback:
     - "strong": "Evidence backs this up — [source] confirms [data]. Lead with this in investor meetings."
     - "contradicted": "Evidence says the opposite — [source] reports [data]. Correct this before an investor checks it."
     - "weak_claim": evidence addresses the same subject and points the same direction, but the claim overstates it (e.g. "fastest-growing" where evidence shows 12% growth). Cite it. "Evidence doesn't fully support this. Consider rephrasing to: '[suggested rewrite based on what evidence actually shows]'"
     - "vague": "Too generic for investors. Based on evidence, you could say: '[specific rewrite with data from evidence]'"
     - "unsubstantiated": "Our research found no evidence for this claim. Either cite a source, soften to a hypothesis ('we believe...'), or remove it."
   - evidence_ref, evidence_quote: see CITATIONS
   Include at least 6 annotations. Be thorough — this is what the founder came here for. Mark claims as "strong" when evidence supports them. For every "vague" or "weak_claim", suggest a specific rewrite.

10. deal_context: Where pitches like this typically sit in the funding landscape.
    - typical_stage: Based on comparable companies found in evidence
    - typical_raise_range: Based on comparable deals in evidence. If none found, say so.
    - typical_dilution: What's typical at this stage
    - red_flags: 2-4 things an investor reviewing this pitch would flag. Each should reference evidence and suggest what the founder can add to address it.

11. feature_suggestions: 3-5 features to mention in the pitch. Evidence shows competitors offer these or users want them — mentioning your approach to them makes the pitch more credible.
    - "Evidence shows [Competitor X] and [Competitor Y] both offer [feature] — addressing how you handle this strengthens your pitch."

""" + EVIDENCE_RULES + verdictRules("unsubstantiated")


def resolveCitation(
    evidenceRef: int | None, evidenceQuote: str | None, evidence: list[EvidenceItem]
) -> Citation | None:
    if evidenceRef is None or not evidenceQuote or not evidenceQuote.strip():
        return None
    if not 1 <= evidenceRef <= len(evidence):
        return None
    item = evidence[evidenceRef - 1]
    return Citation(quote=evidenceQuote.strip(), source_url=item.source_url, retrieved_at=item.retrieved_at)


def writer_node(state: AgentState) -> dict:
    pitch = state["pitch"]
    mode = state.get("mode", "market_scan")
    evidence = state.get("raw_evidence", [])

    prompt = PITCH_LAB_PROMPT if mode == "pitch_lab" else QUICK_CHECK_PROMPT

    evidence_text = "\n\n".join(
        f"[E{i}] Source: {e.source_url}\nRetrieved: {e.retrieved_at.date().isoformat()}\n"
        f"Query: [{e.query}]\nTitle: {e.title}\nContent: {e.snippet}"
        for i, e in enumerate(evidence, start=1)
    )

    result, _ = invokeStructured(
        writer_llm,
        [
            ("system", prompt),
            (
                "human",
                f"Startup Pitch:\n{pitch}\n\nResearch Evidence:\n{evidence_text}",
            ),
        ],
    )

    citation_links = list({str(e.source_url) for e in evidence})

    memo = MemoOutput(
        pitch_score=result.pitch_score,
        subscores=result.subscores,
        strengthen_suggestions=result.strengthen_suggestions,
        executive_summary=result.executive_summary,
        market_matrix=[
            MarketCompetitor(
                competitor=row.competitor,
                pricing=row.pricing,
                funding=row.funding,
                citation=resolveCitation(row.evidence_ref, row.evidence_quote, evidence),
            )
            for row in result.market_matrix
        ],
        risk_vectors=result.risk_vectors,
        confidence_score=result.confidence_score,
        citation_links=citation_links,
        investor_questions=result.investor_questions,
        pitch_annotations=[
            PitchAnnotation(
                excerpt=ann.excerpt,
                annotation_type=ann.annotation_type,
                note=ann.note,
                citation=resolveCitation(ann.evidence_ref, ann.evidence_quote, evidence),
            )
            for ann in result.pitch_annotations
        ],
        deal_context=result.deal_context,
        feature_suggestions=result.feature_suggestions,
    )

    return {"final_memo": memo}
