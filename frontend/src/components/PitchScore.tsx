"use client";

import type { Subscores } from "@/lib/types";

interface Props {
  pitchScore: number;
  subscores: Subscores;
}

const subscoreLabels: { key: keyof Subscores; label: string }[] = [
  { key: "market_size", label: "Market Size" },
  { key: "competition", label: "Competition" },
  { key: "revenue_model", label: "Revenue Model" },
  { key: "uniqueness", label: "Uniqueness" },
];

function scoreColor(value: number): string {
  if (value >= 70) return "bg-[#2D6A4F]";
  if (value >= 40) return "bg-[#B08B2D]";
  return "bg-[#9B2C2C]";
}

function scoreTextColor(value: number): string {
  if (value >= 70) return "text-[#2D6A4F]";
  if (value >= 40) return "text-[#B08B2D]";
  return "text-[#9B2C2C]";
}

export default function PitchScore({ pitchScore, subscores }: Props) {
  return (
    <div className="mb-12">
      <h2 className="font-sans text-xs uppercase tracking-widest text-muted mb-6">
        Pitch Score
      </h2>

      <div className="flex items-baseline gap-2 mb-8">
        <span className={`font-serif text-5xl ${scoreTextColor(pitchScore)}`}>
          {pitchScore}
        </span>
        <span className="font-sans text-lg text-muted">/ 100</span>
      </div>

      <div className="space-y-3">
        {subscoreLabels.map(({ key, label }) => {
          const value = subscores[key];
          return (
            <div key={key} className="flex items-center gap-4">
              <span className="font-sans text-sm text-muted w-32 shrink-0">
                {label}
              </span>
              <div className="flex-1 h-2 bg-border overflow-hidden">
                <div
                  className={`h-full ${scoreColor(value)}`}
                  style={{ width: `${value}%` }}
                />
              </div>
              <span className="font-sans text-sm text-foreground w-8 text-right">
                {value}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
