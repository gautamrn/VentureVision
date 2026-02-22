from pydantic import BaseModel
from langchain_openai import ChatOpenAI

from app.graph.state import AgentState
from app.schemas.models import MarketCompetitor, MemoOutput, Subscores


class MemoSynthesis(BaseModel):
    pitch_score: int
    subscores: Subscores
    strengthen_suggestions: list[str]
    executive_summary: str
    market_matrix: list[MarketCompetitor]
    risk_vectors: list[str]
    confidence_score: float


llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, max_tokens=2048)
writer_llm = llm.with_structured_output(MemoSynthesis)

SYSTEM_PROMPT = """You are a senior venture capital analyst writing a formal due diligence memo.

You will receive a startup pitch and a body of research evidence collected by a search agent.

Your task:
1. pitch_score: An overall score from 0 to 100 rating the strength of this pitch. This is a weighted average of the four subscores below.
2. subscores: Rate each dimension from 0 to 100:
   - market_size: How large and growing is the addressable market?
   - competition: How differentiated is this startup from existing players? (higher = less competition / stronger moat)
   - revenue_model: How clear, viable, and scalable is the revenue model?
   - uniqueness: How novel is the approach, technology, or insight?
3. strengthen_suggestions: 3-5 specific, actionable suggestions to make the pitch stronger. Use founder-friendly language. Examples:
   - "Add your pricing model — none is mentioned"
   - "Clarify what differentiates your API from [competitor]"
   - "Include your go-to-market strategy"
   Do NOT use analyst jargon. Each suggestion should tell the founder exactly what to add or change.
4. executive_summary: 2-3 sentences. Ground every claim in the evidence. No opinions.
5. market_matrix: List real competitors found in the evidence. For each, include:
   - competitor: company name
   - pricing: exact pricing if found, otherwise "not publicly disclosed"
   - funding: funding amount/stage if found, otherwise "unknown"
6. risk_vectors: 3-5 specific risks identified from evidence gaps or market data.
7. confidence_score: 0.0 to 1.0 reflecting how well the evidence covers the pitch claims.
   - 0.8+ = strong coverage, most claims verified
   - 0.5-0.8 = partial coverage, some gaps remain
   - below 0.5 = significant data gaps

CRITICAL RULES:
- Never invent competitor names, pricing, or funding. Use only what the evidence contains.
- If a claim in the pitch cannot be verified from evidence, flag it as a risk vector.
- Do not use phrases like "based on my knowledge" — only cite evidence."""


def writer_node(state: AgentState) -> dict:
    pitch = state["pitch"]
    evidence = state.get("raw_evidence", [])

    evidence_text = "\n\n".join(
        f"Source: {e.source_url}\nQuery: [{e.query}]\nTitle: {e.title}\nContent: {e.snippet}"
        for e in evidence
    )

    result: MemoSynthesis = writer_llm.invoke(
        [
            ("system", SYSTEM_PROMPT),
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
    )

    return {"final_memo": memo}
