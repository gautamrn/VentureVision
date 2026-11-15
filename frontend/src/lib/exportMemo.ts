import type { Citation, MemoOutput, RunSource } from "./types";
import { retrievalDate } from "./citations";
import { AI_DISCLAIMER, formatDuration, formatRunDate, formatUsd } from "./formatRun";

function citationLine(citation: Citation | null | undefined): string | null {
  if (!citation) return null;
  return `  > "${citation.quote}" — ${citation.source_url} (retrieved ${retrievalDate(citation)})`;
}

export function memoToMarkdown(memo: MemoOutput, source: RunSource): string {
  const lines: string[] = [];

  lines.push(`# Pitch Analysis — Score: ${memo.pitch_score}/100`);
  lines.push(
    source.kind === "demo"
      ? `Demo data: recorded pipeline run from ${source.recordedAt.slice(0, 10)}`
      : source.kind === "shared"
        ? `Shared analysis, run ${formatRunDate(source.generatedAt)}. ${AI_DISCLAIMER}`
        : "Live run"
  );
  if (memo.groundedness) {
    const { cited_claims, total_claims, downgraded_claims } = memo.groundedness;
    lines.push(
      `Groundedness: ${cited_claims} of ${total_claims} claims cited` +
        (downgraded_claims > 0 ? ` · ${downgraded_claims} downgraded for missing citations` : "")
    );
  }
  lines.push("");

  lines.push("## Subscores");
  lines.push(`- **Market Size:** ${memo.subscores.market_size}/100`);
  lines.push(`- **Competition:** ${memo.subscores.competition}/100`);
  lines.push(`- **Revenue Model:** ${memo.subscores.revenue_model}/100`);
  lines.push(`- **Uniqueness:** ${memo.subscores.uniqueness}/100`);
  lines.push("");

  if (memo.strengthen_suggestions.length > 0) {
    lines.push("## Strengthen Your Pitch");
    for (const s of memo.strengthen_suggestions) {
      lines.push(`- ${s}`);
    }
    lines.push("");
  }

  lines.push("## Executive Summary");
  lines.push(memo.executive_summary);
  lines.push("");

  if (memo.market_matrix.length > 0) {
    lines.push("## Competitive Landscape");
    lines.push("| Company | Pricing | Funding |");
    lines.push("|---------|---------|---------|");
    for (const c of memo.market_matrix) {
      lines.push(`| ${c.competitor} | ${c.pricing} | ${c.funding} |`);
    }
    lines.push("");
    const citedRows = memo.market_matrix.filter((c) => c.citation);
    for (const c of citedRows) {
      lines.push(`- ${c.competitor}`, citationLine(c.citation) ?? "");
    }
    if (citedRows.length > 0) lines.push("");
  }

  if (memo.investor_questions.length > 0) {
    lines.push("## Investor Q&A — Prepare for These");
    for (const q of memo.investor_questions) {
      lines.push(`- **${q.question}**`);
      lines.push(`  ${q.why_it_matters}`);
    }
    lines.push("");
  }

  lines.push("## Risk Vectors");
  for (const r of memo.risk_vectors) {
    lines.push(`- ${r}`);
  }
  lines.push("");

  lines.push("## Deal Context");
  lines.push(`- **Stage:** ${memo.deal_context.typical_stage}`);
  lines.push(`- **Typical Raise:** ${memo.deal_context.typical_raise_range}`);
  lines.push(`- **Expected Dilution:** ${memo.deal_context.typical_dilution}`);
  if (memo.deal_context.red_flags.length > 0) {
    lines.push("- **Watch out for:**");
    for (const flag of memo.deal_context.red_flags) {
      lines.push(`  - ${flag}`);
    }
  }
  lines.push("");

  if (memo.pitch_annotations.length > 0) {
    lines.push("## Pitch Annotations");
    for (const ann of memo.pitch_annotations) {
      lines.push(`- [${ann.annotation_type}] "${ann.excerpt}" — ${ann.note}`);
      const cite = citationLine(ann.citation);
      if (cite) lines.push(cite);
    }
    lines.push("");
  }

  if (memo.feature_suggestions.length > 0) {
    lines.push("## Features to Consider Building");
    for (const s of memo.feature_suggestions) {
      lines.push(`- ${s}`);
    }
    lines.push("");
  }

  lines.push(`## Research Confidence`);
  lines.push(
    `${Math.round(memo.confidence_score * 100)}% — based on ${memo.citation_links.length} sources`
  );
  lines.push("");

  if (memo.citation_links.length > 0) {
    lines.push("## Sources");
    for (const url of memo.citation_links) {
      lines.push(`- ${url}`);
    }
  }

  if (memo.telemetry) {
    const t = memo.telemetry;
    lines.push("");
    lines.push(
      `This analysis: ${t.agent_count} agents, ${formatDuration(t.duration_ms)}, ~${formatUsd(t.total_cost_usd)}` +
        ` (${t.prompt_tokens + t.completion_tokens} tokens, ${t.search_calls} web searches; prices as of ${t.pricing_as_of})`
    );
    if (t.budget_exit_reason) lines.push(t.budget_exit_reason);
  }

  return lines.join("\n");
}
