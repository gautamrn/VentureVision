"use client";

import { ExternalLink } from "lucide-react";
import type { Citation } from "@/lib/types";
import { retrievalDate, sourceHost } from "@/lib/citations";

interface MarkerProps {
  number: number;
  expanded: boolean;
  onToggle: () => void;
}

export function CitationMarker({ number, expanded, onToggle }: MarkerProps) {
  return (
    <button
      type="button"
      onClick={onToggle}
      aria-expanded={expanded}
      aria-label={`${expanded ? "Hide" : "Show"} evidence for citation ${number}`}
      className={`font-sans text-[10px] leading-none align-super ml-1 px-1 py-0.5 border rounded-sm ${
        expanded
          ? "border-foreground text-foreground"
          : "border-border text-muted hover:text-foreground hover:border-foreground"
      }`}
    >
      [{number}]
    </button>
  );
}

export function CitationQuote({ number, citation }: { number: number; citation: Citation }) {
  return (
    <blockquote className="mt-2 border-l-2 border-foreground/30 pl-3 py-1">
      <p className="font-serif text-sm text-foreground leading-relaxed">
        &ldquo;{citation.quote}&rdquo;
      </p>
      <p className="font-sans text-[11px] text-muted mt-1 flex flex-wrap items-center gap-x-3 gap-y-1">
        <span className="text-foreground">[{number}]</span>
        <a
          href={citation.source_url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 hover:text-foreground break-all"
        >
          <ExternalLink size={10} className="shrink-0" />
          {sourceHost(citation)}
        </a>
        <span>Retrieved {retrievalDate(citation)}</span>
      </p>
    </blockquote>
  );
}
