import type { MemoOutput } from "./types";

export function memoToMarkdown(memo: MemoOutput): string {
  const lines: string[] = [];

  lines.push(`# Pitch Analysis — Score: ${memo.pitch_score}/100`);
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
  }

  lines.push("## Risk Vectors");
  for (const r of memo.risk_vectors) {
    lines.push(`- ${r}`);
  }
  lines.push("");

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

  return lines.join("\n");
}
