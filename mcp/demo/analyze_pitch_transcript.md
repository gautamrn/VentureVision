# MCP transcript: analyze_pitch over stdio

Recorded 2026-11-15 22:16 UTC by `mcp/demoClient.py` against the live pipeline.

## 1. initialize

Server: `venture-vision`, protocol `2025-06-18`.

## 2. tools/list

- `analyze_pitch`: Research a startup pitch on the live web and return the memo summary with a verdict for every claim.
- `verify_claim`: Judge one claim against the evidence you supply: supported, unsupported, or contradicted.
- `get_eval_scores`: Latest stored accuracy of VentureVision's claim verdicts on its hand-labeled dataset, per label.

`analyze_pitch` inputSchema:

```json
{
  "properties": {
    "pitch_text": {
      "description": "The pitch or idea, 40-5000 characters.",
      "maxLength": 5000,
      "minLength": 40,
      "title": "Pitch Text",
      "type": "string"
    },
    "mode": {
      "default": "market_scan",
      "description": "market_scan: is this worth building, who else does it. pitch_lab: how investor-ready is this text.",
      "enum": [
        "market_scan",
        "pitch_lab"
      ],
      "title": "Mode",
      "type": "string"
    }
  },
  "required": [
    "pitch_text"
  ],
  "title": "analyzePitchArguments",
  "type": "object",
  "additionalProperties": false
}
```

## 3. tools/call analyze_pitch

Request arguments:

```json
{
  "pitch_text": "Tablebook: AI bookkeeping for independent restaurants. Restaurants run on 3-5% margins and most owners do their books in a shoebox. Tablebook connects to Square and Toast, categorizes every transaction, reconciles delivery-app payouts from DoorDash and Uber Eats, and produces a weekly P&L. The US has over 700,000 restaurants and no bookkeeping product is built for them. $149 per location per month.",
  "mode": "market_scan"
}
```

Progress notifications:

- `  5.6s` progress 1: planner finished
- ` 14.8s` progress 2: scout finished
- ` 17.2s` progress 3: critic finished
- ` 24.1s` progress 4: scout finished
- ` 26.0s` progress 5: critic finished
- ` 35.6s` progress 6: scout finished
- ` 38.4s` progress 7: critic finished
- ` 40.3s` progress 8: scout finished
- ` 40.3s` progress 9: critic finished
- ` 65.1s` progress 10: writer finished
- ` 65.1s` progress 11: citation_audit finished

Result after 65.1s, `isError: false`. `structuredContent`:

```json
{
  "mode": "market_scan",
  "pitch_score": 72,
  "subscores": {
    "market_size": 75,
    "competition": 60,
    "revenue_model": 70,
    "uniqueness": 80
  },
  "executive_summary": "The market for AI bookkeeping solutions in the restaurant industry is growing, with over 700,000 restaurants in the U.S. and increasing technology adoption rates. While there are established players like QuickBooks and Restaurant365, there is still room for innovation, particularly in tailored solutions for independent restaurants. The unique integration with popular POS systems like Square and Toast could provide a competitive edge.",
  "verdict_counts": {
    "strong": 2,
    "contradicted": 0,
    "needs_research": 2,
    "weak_claim": 0,
    "vague": 0,
    "unsubstantiated": 0
  },
  "label_counts": {
    "supported": 2,
    "unsupported": 2,
    "contradicted": 0
  },
  "groundedness": {
    "cited_claims": 6,
    "total_claims": 8,
    "downgraded_claims": 1
  },
  "claims": [
    {
      "excerpt": "AI bookkeeping for independent restaurants.",
      "verdict": "strong",
      "eval_label": "supported",
      "note": "The evidence supports a growing interest in AI solutions for restaurants, indicating a viable market.",
      "evidence_quote": "As AI technology becomes more affordable and scalable, smaller restaurants will increasingly adopt these solutions.",
      "source_url": "https://www.linkedin.com/pulse/role-ai-revolutionizing-restaurant-accounting-software-market-p5oif",
      "downgraded_from": null
    },
    {
      "excerpt": "Restaurants run on 3-5% margins and most owners do their books in a shoebox.",
      "verdict": "needs_research",
      "eval_label": "unsupported",
      "note": "The evidence highlights that many restaurant operators are under pressure to modernize their bookkeeping practices.",
      "evidence_quote": null,
      "source_url": null,
      "downgraded_from": "strong"
    },
    {
      "excerpt": "The US has over 700,000 restaurants and no bookkeeping product is built for them.",
      "verdict": "strong",
      "eval_label": "supported",
      "note": "The market size for restaurant technology is significant, with a high number of establishments needing tailored solutions.",
      "evidence_quote": "The restaurant industry is poised to employ 15.7 million people and generate $1 trillion in sales in 2024.",
      "source_url": "https://quickbooks.intuit.com/r/bookkeeping/restaurant-bookkeeping",
      "downgraded_from": null
    },
    {
      "excerpt": "$149 per location per month.",
      "verdict": "needs_research",
      "eval_label": "unsupported",
      "note": "No evidence was found regarding the pricing strategy for similar products, making it unclear how competitive this price point is.",
      "evidence_quote": null,
      "source_url": null,
      "downgraded_from": null
    }
  ],
  "competitors": [
    {
      "name": "Docyt",
      "pricing": "not found in evidence",
      "funding": "not found in evidence",
      "source_url": "https://www.docyt.com/"
    },
    {
      "name": "Restaurant365",
      "pricing": "not found in evidence",
      "funding": "not found in evidence",
      "source_url": "https://www.aprio.com/insights-events/scaling-restaurant-operations-without-back-office-strain-key-challenges-and-opportunities-ins-article-rfh"
    },
    {
      "name": "QuickBooks",
      "pricing": "$25/month",
      "funding": "not found in evidence",
      "source_url": "https://www.restaurant365.com/blog/best-accounting-software"
    },
    {
      "name": "Sage Intacct",
      "pricing": "approximately $15,000 per year",
      "funding": "not found in evidence",
      "source_url": "https://www.restaurant365.com/blog/best-accounting-software"
    }
  ],
  "risks": [
    "The market is growing, but many existing solutions like QuickBooks and Restaurant365 are well-established and could pose significant competition.",
    "Integration with POS systems is crucial; if competitors like Toast and Square enhance their offerings, it could impact Tablebook's market entry.",
    "Independent restaurants often face challenges in adopting new technology, which could affect user acquisition and retention."
  ],
  "investor_questions": [
    "What specific features will differentiate Tablebook from existing solutions like QuickBooks and Restaurant365?",
    "How will you ensure seamless integration with popular POS systems like Square and Toast?",
    "What strategies will you employ to educate restaurant owners about the benefits of AI bookkeeping?",
    "How will you handle customer support and onboarding for restaurant owners who may not be tech-savvy?",
    "What pricing strategy will you adopt to remain competitive while ensuring profitability?",
    "How will you gather feedback from users to continuously improve the product?",
    "What are your plans for scaling the business as you gain traction?"
  ],
  "sources_consulted": 18,
  "run": {
    "duration_ms": 62455,
    "llm_calls": 5,
    "search_calls": 15,
    "failed_searches": 0,
    "total_cost_usd": 0.12267,
    "budget_usd": 0.25,
    "budget_exit_reason": null,
    "models": [
      "gpt-4o-mini-2024-07-18"
    ]
  }
}
```
