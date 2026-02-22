"use client";

import { ExternalLink } from "lucide-react";
import type { MemoOutput } from "@/lib/types";

interface Props {
  memo: MemoOutput;
}

export default function MemoDocument({ memo }: Props) {
  return (
    <article className="font-serif text-foreground">
      <section className="mb-12">
        <h2 className="font-sans text-xs uppercase tracking-widest text-muted mb-4">
          Executive Summary
        </h2>
        <p className="text-lg leading-relaxed">{memo.executive_summary}</p>
      </section>

      <section className="mb-12">
        <h2 className="font-sans text-xs uppercase tracking-widest text-muted mb-4">
          Competitive Landscape
        </h2>
        {memo.market_matrix.length === 0 ? (
          <p className="text-base text-muted">No competitor data found.</p>
        ) : (
          <table className="w-full text-sm">
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
        )}
      </section>

      <section className="mb-12">
        <h2 className="font-sans text-xs uppercase tracking-widest text-muted mb-4">
          Risk Vectors
        </h2>
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
                className="font-sans text-xs text-muted flex items-center gap-1 hover:text-foreground"
              >
                <ExternalLink size={10} />
                {url}
              </a>
            </li>
          ))}
        </ul>
      </section>
    </article>
  );
}
