"use client";

import type { PitchAnnotation } from "@/lib/types";

interface Props {
  pitch: string;
  annotations: PitchAnnotation[];
}

const typeColors: Record<string, { bg: string; border: string; label: string }> = {
  weak_claim: { bg: "bg-[#9B2C2C]/10", border: "border-[#9B2C2C]/30", label: "Weak claim" },
  vague: { bg: "bg-[#B08B2D]/10", border: "border-[#B08B2D]/30", label: "Vague" },
  unsubstantiated: { bg: "bg-[#9B2C2C]/10", border: "border-[#9B2C2C]/30", label: "Unsubstantiated" },
  strong: { bg: "bg-[#2D6A4F]/10", border: "border-[#2D6A4F]/30", label: "Supported" },
};

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

export default function PitchAnnotations({ pitch, annotations }: Props) {
  if (annotations.length === 0) return null;

  const segments = buildAnnotatedPitch(pitch, annotations);
  const annotatedItems = annotations.filter((a) =>
    pitch.toLowerCase().includes(a.excerpt.toLowerCase())
  );

  return (
    <section className="mb-12">
      <h2 className="font-sans text-xs uppercase tracking-widest text-muted mb-4">
        How an Investor Reads Your Pitch
      </h2>

      <div className="border border-border p-4 mb-6">
        <p className="font-sans text-sm text-foreground leading-relaxed whitespace-pre-wrap">
          {segments.map((seg, i) => {
            if (!seg.annotation) return <span key={i}>{seg.text}</span>;
            const colors = typeColors[seg.annotation.annotation_type] ?? typeColors.vague;
            return (
              <mark
                key={i}
                className={`${colors.bg} px-0.5 border-b-2 ${colors.border}`}
                title={seg.annotation.note}
              >
                {seg.text}
              </mark>
            );
          })}
        </p>
      </div>

      <ul className="space-y-3">
        {annotatedItems.map((ann, i) => {
          const colors = typeColors[ann.annotation_type] ?? typeColors.vague;
          return (
            <li key={i} className="flex items-start gap-3">
              <span className={`font-sans text-xs px-1.5 py-0.5 ${colors.bg} shrink-0 mt-0.5`}>
                {colors.label}
              </span>
              <div>
                <p className="font-sans text-xs text-foreground">
                  &ldquo;{ann.excerpt}&rdquo;
                </p>
                <p className="font-sans text-xs text-muted mt-0.5">
                  {ann.note}
                </p>
              </div>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
