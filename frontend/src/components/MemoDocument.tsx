"use client";

import { useState } from "react";
import { ExternalLink, Clipboard, Check } from "lucide-react";
import type { MemoOutput } from "@/lib/types";
import { memoToMarkdown } from "@/lib/exportMemo";
import StrengthenPitch from "./StrengthenPitch";

interface Props {
  memo: MemoOutput;
}

function CopyButton({ text, label }: { text: string; label?: string }) {
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <button
      onClick={handleCopy}
      className="inline-flex items-center gap-1 text-xs font-sans text-muted hover:text-foreground"
    >
      {copied ? <Check size={10} /> : <Clipboard size={10} />}
      {label ?? (copied ? "Copied" : "Copy")}
    </button>
  );
}

function competitorTableToText(memo: MemoOutput): string {
  if (memo.market_matrix.length === 0) return "No competitor data found.";
  const header = "Company | Pricing | Funding";
  const divider = "---|---|---";
  const rows = memo.market_matrix.map(
    (c) => `${c.competitor} | ${c.pricing} | ${c.funding}`
  );
  return [header, divider, ...rows].join("\n");
}

export default function MemoDocument({ memo }: Props) {
  return (
    <article className="font-serif text-foreground">
      <div className="flex justify-end mb-6">
        <CopyButton text={memoToMarkdown(memo)} label="Copy as Markdown" />
      </div>

      <StrengthenPitch suggestions={memo.strengthen_suggestions} />

      <section className="mb-12">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-sans text-xs uppercase tracking-widest text-muted">
            Executive Summary
          </h2>
          <CopyButton text={memo.executive_summary} />
        </div>
        <p className="text-lg leading-relaxed">{memo.executive_summary}</p>
      </section>

      <section className="mb-12">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-sans text-xs uppercase tracking-widest text-muted">
            Competitive Landscape
          </h2>
          {memo.market_matrix.length > 0 && (
            <CopyButton text={competitorTableToText(memo)} />
          )}
        </div>
        {memo.market_matrix.length === 0 ? (
          <p className="text-base text-muted">No competitor data found.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm min-w-[400px]">
              <thead>
                <tr className="border-b border-border">
                  <th className="font-sans text-left pb-2 text-muted font-normal">
                    Company
                  </th>
                  <th className="font-sans text-left pb-2 text-muted font-normal">
                    Pricing
                  </th>
                  <th className="font-sans text-left pb-2 text-muted font-normal">
                    Funding
                  </th>
                </tr>
              </thead>
              <tbody>
                {memo.market_matrix.map((c, i) => (
                  <tr key={i} className="border-b border-border">
                    <td className="py-3">{c.competitor}</td>
                    <td className="py-3 text-muted font-sans">{c.pricing}</td>
                    <td className="py-3 text-muted font-sans">{c.funding}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="mb-12">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-sans text-xs uppercase tracking-widest text-muted">
            Risk Vectors
          </h2>
          <CopyButton text={memo.risk_vectors.join("\n")} />
        </div>
        <ul className="space-y-2">
          {memo.risk_vectors.map((risk, i) => (
            <li key={i} className="text-base leading-relaxed">
              {risk}
            </li>
          ))}
        </ul>
      </section>

      <section className="mb-12">
        <h2 className="font-sans text-xs uppercase tracking-widest text-muted mb-4">
          Research Confidence
        </h2>
        <p className="text-base">
          {Math.round(memo.confidence_score * 100)}% — based on{" "}
          {memo.citation_links.length} verified sources
        </p>
      </section>

      <section>
        <h2 className="font-sans text-xs uppercase tracking-widest text-muted mb-4">
          Sources
        </h2>
        <ul className="space-y-2">
          {memo.citation_links.map((url, i) => (
            <li key={i}>
              <a
                href={url}
                target="_blank"
                rel="noopener noreferrer"
                className="font-sans text-xs text-muted flex items-center gap-1 hover:text-foreground break-all"
              >
                <ExternalLink size={10} className="shrink-0" />
                {url}
              </a>
            </li>
          ))}
        </ul>
      </section>
    </article>
  );
}
