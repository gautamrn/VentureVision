"use client";

import { CircleAlert } from "lucide-react";

interface Props {
  suggestions: string[];
}

export default function StrengthenPitch({ suggestions }: Props) {
  if (suggestions.length === 0) return null;

  return (
    <section className="mb-12">
      <h2 className="font-sans text-xs uppercase tracking-widest text-muted mb-4">
        Strengthen Your Pitch
      </h2>
      <ul className="space-y-3">
        {suggestions.map((suggestion, i) => (
          <li key={i} className="flex items-start gap-3">
            <CircleAlert size={14} className="text-[#B08B2D] mt-1 shrink-0" />
            <span className="font-sans text-sm text-foreground leading-relaxed">
              {suggestion}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}
