"use client";

import type { InvestorQuestion } from "@/lib/types";

interface Props {
  questions: InvestorQuestion[];
}

export default function InvestorQA({ questions }: Props) {
  if (questions.length === 0) return null;

  return (
    <section className="mb-12">
      <h2 className="font-sans text-xs uppercase tracking-widest text-muted mb-4">
        Investor Q&A — Prepare for These
      </h2>
      <ul className="space-y-4">
        {questions.map((q, i) => (
          <li key={i}>
            <p className="font-sans text-sm text-foreground font-medium">
              {q.question}
            </p>
            <p className="font-sans text-xs text-muted mt-1">
              {q.why_it_matters}
            </p>
          </li>
        ))}
      </ul>
    </section>
  );
}
