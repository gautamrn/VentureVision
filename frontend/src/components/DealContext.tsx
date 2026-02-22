"use client";

import { AlertTriangle } from "lucide-react";
import type { DealContext as DealContextType } from "@/lib/types";

interface Props {
  dealContext: DealContextType;
}

export default function DealContext({ dealContext }: Props) {
  return (
    <section className="mb-12">
      <h2 className="font-sans text-xs uppercase tracking-widest text-muted mb-4">
        Deal Context
      </h2>

      <div className="grid grid-cols-3 gap-4 mb-6">
        <div>
          <p className="font-sans text-xs text-muted">Stage</p>
          <p className="font-sans text-sm text-foreground mt-1">
            {dealContext.typical_stage}
          </p>
        </div>
        <div>
          <p className="font-sans text-xs text-muted">Typical Raise</p>
          <p className="font-sans text-sm text-foreground mt-1">
            {dealContext.typical_raise_range}
          </p>
        </div>
        <div>
          <p className="font-sans text-xs text-muted">Expected Dilution</p>
          <p className="font-sans text-sm text-foreground mt-1">
            {dealContext.typical_dilution}
          </p>
        </div>
      </div>

      {dealContext.red_flags.length > 0 && (
        <div>
          <p className="font-sans text-xs text-muted mb-2">Watch out for</p>
          <ul className="space-y-2">
            {dealContext.red_flags.map((flag, i) => (
              <li key={i} className="flex items-start gap-2">
                <AlertTriangle size={12} className="text-[#9B2C2C] mt-0.5 shrink-0" />
                <span className="font-sans text-xs text-foreground">{flag}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
