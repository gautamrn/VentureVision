"use client";

import { useState } from "react";
import type { PitchAnnotation } from "@/lib/types";
import { CitationMarker, CitationQuote } from "./Citation";

interface Props {
  pitch: string;
  annotations: PitchAnnotation[];
  citationNumbers: (number | null)[];
}

const RED = { bg: "bg-[#9B2C2C]/10", border: "border-[#9B2C2C]/30", text: "text-foreground" };
const AMBER = { bg: "bg-[#B08B2D]/10", border: "border-[#B08B2D]/30", text: "text-foreground" };

const typeColors: Record<string, { bg: string; border: string; text: string; label: string }> = {
  strong: { bg: "bg-[#2D6A4F]/10", border: "border-[#2D6A4F]/30", text: "text-foreground", label: "Supported" },
  contradicted: {
    bg: "bg-[#9B2C2C]/15",
    border: "border-[#9B2C2C]/60",
    text: "text-[#9B2C2C]",
    label: "Contradicted",
  },
  needs_research: { ...AMBER, label: "Needs research" },
  unsubstantiated: { ...AMBER, label: "Unsubstantiated" },
  vague: { ...AMBER, label: "Vague" },
  weak_claim: { ...RED, label: "Weak claim" },
};

function colorsFor(annotationType: string) {
  return typeColors[annotationType] ?? typeColors.vague;
}

function buildAnnotatedPitch(pitch: string, annotations: PitchAnnotation[]) {
  const sorted = [...annotations].sort((a, b) => {
    const indexA = pitch.toLowerCase().indexOf(a.excerpt.toLowerCase());
    const indexB = pitch.toLowerCase().indexOf(b.excerpt.toLowerCase());
    return indexA - indexB;
  });

  const segments: { text: string; annotation?: PitchAnnotation }[] = [];
  let cursor = 0;

  for (const ann of sorted) {
    const idx = pitch.toLowerCase().indexOf(ann.excerpt.toLowerCase(), cursor);
    if (idx === -1) continue;

    if (idx > cursor) {
      segments.push({ text: pitch.slice(cursor, idx) });
    }

    segments.push({
      text: pitch.slice(idx, idx + ann.excerpt.length),
      annotation: ann,
    });

    cursor = idx + ann.excerpt.length;
  }

  if (cursor < pitch.length) {
    segments.push({ text: pitch.slice(cursor) });
  }

  return segments;
}

export default function PitchAnnotations({ pitch, annotations, citationNumbers }: Props) {
  const [expanded, setExpanded] = useState<Set<number>>(new Set());

  if (annotations.length === 0) return null;

  const segments = buildAnnotatedPitch(pitch, annotations);
  const numberOf = new Map(annotations.map((ann, i) => [ann, citationNumbers[i]]));

  function toggle(index: number) {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(index)) next.delete(index);
      else next.add(index);
      return next;
    });
  }

  return (
    <section className="mb-12">
      <h2 className="font-sans text-xs uppercase tracking-widest text-muted mb-4">
        How an Investor Reads Your Pitch
      </h2>

      <div className="border border-border p-4 mb-6">
        <p className="font-sans text-sm text-foreground leading-relaxed whitespace-pre-wrap">
          {segments.map((seg, i) => {
            if (!seg.annotation) return <span key={i}>{seg.text}</span>;
            const colors = colorsFor(seg.annotation.annotation_type);
            const number = numberOf.get(seg.annotation);
            return (
              <span key={i}>
                <mark
                  className={`${colors.bg} px-0.5 border-b-2 ${colors.border}`}
                  title={seg.annotation.note}
                >
                  {seg.text}
                </mark>
                {number != null && (
                  <sup className="font-sans text-[10px] text-muted ml-0.5">[{number}]</sup>
                )}
              </span>
            );
          })}
        </p>
      </div>

      <ul className="space-y-3">
        {annotations.map((ann, i) => {
          const colors = colorsFor(ann.annotation_type);
          const number = citationNumbers[i];
          return (
            <li key={i} className="flex items-start gap-3">
              <span
                className={`font-sans text-xs px-1.5 py-0.5 border ${colors.bg} ${colors.border} ${colors.text} shrink-0 mt-0.5 rounded-sm`}
              >
                {colors.label}
              </span>
              <div className="min-w-0 flex-1">
                <p className="font-sans text-xs text-foreground">
                  &ldquo;{ann.excerpt}&rdquo;
                  {number != null && (
                    <CitationMarker number={number} expanded={expanded.has(i)} onToggle={() => toggle(i)} />
                  )}
                </p>
                <p className="font-sans text-xs text-muted mt-0.5">{ann.note}</p>
                {ann.downgraded_from && (
                  <p className="font-sans text-[11px] text-muted mt-0.5">
                    Downgraded from {colorsFor(ann.downgraded_from).label}: no verifiable citation in the evidence.
                  </p>
                )}
                {number != null && ann.citation && expanded.has(i) && (
                  <CitationQuote number={number} citation={ann.citation} />
                )}
              </div>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
