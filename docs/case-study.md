# VentureVision case study

VentureVision reads a startup pitch, researches it on the live web, and returns an investment memo in which every "this claim is backed" verdict has to point at a quote that was actually retrieved. This document covers what it is for, the three decisions that were hardest to get right, what the evals do and do not show, and what to build next.

Every number below comes from a file in this repository. The file is named next to each number. Where a number would matter but has not been measured, it says `[MISSING: ...]` instead of an estimate.

## The problem

Most LLM "startup analyzers" are a single prompt wrapped in a UI. They write fluent, confident memos, invent competitors, and cite nothing. In due diligence, the citation *is* the work: a claim with no source is a claim someone still has to check.

The engineering problem is narrower than "make the model smarter": make a pipeline in which an unsupported claim is visible as unsupported. The pipeline should prefer "not found in evidence" over a plausible guess, and it should be measurable how often its verdicts are right.

## Who it is for

- **Founders sharpening a pitch** (Pitch Lab mode). The memo highlights each claim in their own text and says how an investor would read it: supported, contradicted, needs research, vague, weak, or unsubstantiated.
- **Anyone sanity-checking an idea** (Market Scan mode): who else is in the space, at what price, with what funding, as far as the evidence shows.
- **Developers working in an editor.** The same pipeline is an MCP server (`mcp/`) with `analyze_pitch`, `verify_claim`, and `get_eval_scores`, usable from Cursor or Claude Code.

Usage: [MISSING: number of real users or live runs; the app records per-run metrics in memory only (`/admin`), and nothing persists them across restarts].

## How it works, briefly

A LangGraph state machine runs Planner → Scout → Critic, looping back to Scout while the Critic judges the evidence insufficient (capped at 3 rounds in Market Scan and 4 in Pitch Lab, `backend/app/nodes/critic.py`). It then runs Writer → Citation audit. The planner, critic, and writer each call OpenAI `gpt-4o-mini`, and the Scout calls Tavily search. Every node streams its output to the browser over server-sent events, and every event is validated with Zod on arrival. Runs are capped at a $0.25 budget (`backend/app/telemetry/budget.py`), 5 runs per hour per IP, and 5 active runs at once (`backend/app/middleware/rateLimiter.py`, `backend/app/runs/registry.py`). The architecture diagram is in the README.

## The three hardest decisions

### 1. Grounding is checked mechanically, after writing, and failures are downgraded rather than hidden

**Decision.** The writer may mark a pitch claim `strong` (supported) or `contradicted` only with a citation: a quote of at least three words that must appear verbatim in the retrieved snippet or title of the cited URL. The comparison is after case, whitespace, and typographic-quote normalization (`backend/app/verification/grounding.py`). After the writer runs, a separate `citation_audit` node checks every citation. A strong or contradicted claim without a grounded quote is downgraded to `needs_research` and labeled "Downgraded from Supported: no verifiable citation in the evidence" in the memo. The memo header shows a groundedness line: claims cited, claims total, claims downgraded.

**Why.** Prompting a model to "only use the evidence" is a request, not a guarantee. A string-containment check is cheap, deterministic, and testable, and it catches fabricated quotes outright.

**Cost.** It checks that a quote *exists*, not that it *supports* the claim. The recorded MCP run (`mcp/demo/analyze_pitch_transcript.md`) shows the gap. The pitch claim "The US has over 700,000 restaurants and no bookkeeping product is built for them" was marked `strong` with the quote "The restaurant industry is poised to employ 15.7 million people and generate $1 trillion in sales in 2024." The quote is real and verbatim, but it says nothing about bookkeeping products, and it was retrieved from a QuickBooks restaurant-bookkeeping page. The check also downgrades true claims that cannot be on the public web, such as a founder's own traction numbers. The Pantry demo memo (`frontend/src/data/demo/pantry.json`) ends with 2 of 8 claims cited and 2 downgraded, one of them the traction line.

### 2. The CI gate scores a heuristic, not the model, on a small hand-labeled set

**Decision.** `evals/golden_dataset.jsonl` holds 36 hand-labeled cases (12 supported, 12 unsupported, 12 contradicted). Each pairs a claim with fixed evidence. 14 cases come from real demo-run outputs, including real model mistakes (`seed-real`), and 22 were written to test one verdict boundary each (`seed-constructed`). Every evidence quote is verbatim from a source the Scout retrieved. Two verifiers can be scored on it:

- A model-free heuristic baseline (`backend/app/verification/heuristic.py`) that uses word overlap, typed number comparison, and negation and direction cues.
- An LLM claim verifier (`backend/app/verification/claimVerifier.py`) that uses the same grounding rule as the citation audit.

CI runs only the heuristic and fails a pull request if its accuracy drops more than 3 points below the stored baseline (`.github/workflows/ci.yml`, `evals/results/baseline_heuristic.json`).

**Why.** A CI gate has to be free, deterministic, and fast, and it must not need an API key in CI. A small, honest, versioned dataset beats no dataset. Real model errors make better test cases than invented ones.

**Cost.**

- The number CI protects is not the number users experience. The heuristic is not in the production path, and the LLM verifier has not been scored yet (see below).
- 36 cases is small: one case is 2.8 points.
- The same person wrote the labels and the heuristic, so the heuristic score is likely an upper bound.
- Labels can be genuinely ambiguous. Case `uns-05` pairs the pitch claim "The average US household throws away about 30% of the food it buys, roughly $1,500 a year" with the quote "The average American spends more than $762 per year on food that ends up wasted." The live model called that claim supported. The dataset labels it unsupported, because a per-person figure neither confirms nor refutes a per-household one. The heuristic calls it contradicted.

### 3. The server signs memos instead of storing pitches

**Decision.** Pitches are stored only in the browser's `localStorage`. When a run finishes, the server signs the pitch, mode, timestamp, and memo with an HMAC key (`backend/app/shares/sealing.py`). Later requests that need to trust a memo, such as creating a share link or sending verdict feedback, re-send the memo with its seal, and the server verifies the signature instead of looking anything up. Feedback stores only the claim, the sentence around it, and its evidence, never the whole pitch (`backend/app/feedback/store.py`).

**Why.** Pitches are often confidential. Signing gives provenance (this server produced this exact memo, untouched) without a server-side database of everyone's ideas. Feedback built on top of it cannot be used to inject invented claims into the eval pipeline, because the server re-reads the claim and evidence from the signed memo.

**Cost.**

- Demo replays are recorded fixtures with no seal, so feedback on them is stored but marked `unverified`.
- Without a configured `SHARE_SIGNING_KEY`, the key is per-process, and seals stop verifying after a restart.
- Rotating the key invalidates every memo signed before.
- History is per-browser. There is no account to sync it across devices.

## Evals: what the numbers are, exactly

All accuracy numbers below score **the verdict step only**: given a claim and fixed evidence, is the label right? They do not score web retrieval, the competitor table, or anything else in the memo.

| What was measured | Dataset | Result | Source |
|---|---|---|---|
| **Heuristic baseline** (no model) | golden set v1, 36 cases | **83.3% (30/36)**: supported 100% (12/12), unsupported 91.7% (11/12), contradicted 58.3% (7/12) | `evals/results/baseline_heuristic.json`, run 2026-11-15 22:00 UTC |
| **LLM claim verifier** (`gpt-4o-mini`) | golden set v1, 36 cases | [MISSING: accuracy per label and total cost; run `python evals/run_evals.py --mode llm --publish`] | not run |
| **Live pipeline verdicts** (the writer's labels in real memos) | none | [MISSING: no labeled set of end-to-end memo verdicts exists; the feedback loop is how one would be built] | not measured |
| **Reader feedback** | `feedback` table | 0 rows, 0 candidates, 0 promoted cases. The feature shipped empty | `evals/candidates.jsonl` |

The heuristic's six misses are listed on `/evals`. Five are contradicted cases it called unsupported or supported, and the sixth is the ambiguous `uns-05` above.

### Cost and latency of single recorded runs

These are individual runs, not averages. Each is labeled with the run it came from.

| Run | Mode | Duration | Cost | Model calls | Searches | Claims cited / total (downgraded) |
|---|---|---|---|---|---|---|
| Flakeguard demo, 2026-11-15 | Pitch Lab | 39.6 s | $0.066 | 3 | 8 | 6 / 8 (1) |
| Pantry demo, 2026-11-15 | Pitch Lab | 62.6 s | $0.180 | 6 | 22 | 2 / 8 (2) |
| Thermalith demo, 2026-11-15 | Pitch Lab | 37.1 s | $0.066 | 3 | 8 | 5 / 9 (1) |
| Tablebook via MCP over stdio, 2026-11-15 | Market Scan | 62.5 s | $0.123 | 5 | 15 | 6 / 8 (1) |

Sources: `frontend/src/data/demo/*.json` (the `citation_audit` event's telemetry) and `mcp/demo/analyze_pitch_transcript.md`.

Search, not the model, dominates cost. The Pantry run spent $0.0044 on 6 model calls and $0.18 on 22 searches. More Critic rounds mean more searches, so the Critic's loop cap is effectively the cost control.

Distribution across live runs: [MISSING: p50 and p95 duration and cost over a set of live runs; per-run telemetry exists but is not persisted].

## What I would build next

1. **Score the LLM verifier.** Run `--mode llm` on v1 and publish it next to the heuristic. That is the first number about the model rather than the baseline.
2. **Close the "quote exists but does not support" gap.** If the verifier scores well, run it inside `citation_audit` on every strong or contradicted claim, so a real-but-irrelevant quote gets downgraded too.
3. **Grow the golden set from feedback.** Review disagreements on `/admin`, export with `scripts.exportFeedback`, promote by hand, and bump the dataset version. Prioritize "model said supported, reader said wrong", the cases the grounding check cannot catch.
4. **Evaluate retrieval separately.** Today a wrong verdict and a bad search look the same. A small set of claims with known-good sources would separate "found the wrong page" from "misread the right page".
5. **Persist run telemetry** (and rate-limit counters) outside process memory, so latency and cost can be reported as distributions instead of single runs.
