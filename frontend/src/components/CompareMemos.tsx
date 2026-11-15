import PitchScore from "./PitchScore";
import MemoDocument from "./MemoDocument";
import { formatRunDate, formatUsd } from "@/lib/formatRun";
import type { MemoOutput, RunSource } from "@/lib/types";

export interface ComparedMemo {
  pitch: string;
  memo: MemoOutput;
  source: RunSource;
  runDate?: string | null;
}

function excerpt(text: string, length = 70): string {
  return text.length > length ? `${text.slice(0, length)}…` : text;
}

const ROWS: { label: string; value: (m: ComparedMemo) => string }[] = [
  { label: "Run", value: (m) => (m.runDate ? formatRunDate(m.runDate) : "—") },
  { label: "Pitch score", value: (m) => `${m.memo.pitch_score} / 100` },
  { label: "Market size", value: (m) => String(m.memo.subscores.market_size) },
  { label: "Competition", value: (m) => String(m.memo.subscores.competition) },
  { label: "Revenue model", value: (m) => String(m.memo.subscores.revenue_model) },
  { label: "Uniqueness", value: (m) => String(m.memo.subscores.uniqueness) },
  {
    label: "Groundedness",
    value: (m) =>
      m.memo.groundedness ? `${m.memo.groundedness.cited_claims} of ${m.memo.groundedness.total_claims} claims cited` : "not recorded",
  },
  { label: "Research confidence", value: (m) => `${Math.round(m.memo.confidence_score * 100)}%` },
  { label: "Run cost", value: (m) => (m.memo.telemetry ? `~${formatUsd(m.memo.telemetry.total_cost_usd)}` : "not recorded") },
];

export default function CompareMemos({ left, right }: { left: ComparedMemo; right: ComparedMemo }) {
  return (
    <>
      <table className="w-full font-sans text-xs mb-12 border-t border-border print-keep">
        <thead>
          <tr className="border-b border-border">
            <th className="w-24 sm:w-36" />
            {[left, right].map((m, i) => (
              <th key={i} className="text-left font-normal text-foreground py-2 pr-4 align-top">
                {excerpt(m.pitch)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {ROWS.map((row) => (
            <tr key={row.label} className="border-b border-border">
              <td className="py-1.5 pr-2 text-muted uppercase tracking-wider text-[10px]">{row.label}</td>
              <td className="py-1.5 pr-4 text-foreground tabular-nums">{row.value(left)}</td>
              <td className="py-1.5 pr-4 text-foreground tabular-nums">{row.value(right)}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 print:block">
        {[left, right].map((m, i) => (
          <div
            key={i}
            className={i === 0 ? "md:border-r md:border-border md:pr-8 print:border-0 print:pr-0" : "print:break-before-page"}
          >
            <p className="hidden print:block font-sans text-[9pt] uppercase tracking-widest text-muted mb-2">
              {i === 0 ? "Left" : "Right"} analysis
            </p>
            <p className="font-serif text-lg text-foreground leading-snug mb-8">{excerpt(m.pitch, 120)}</p>
            <PitchScore pitchScore={m.memo.pitch_score} subscores={m.memo.subscores} />
            <MemoDocument memo={m.memo} pitch={m.pitch} source={m.source} />
          </div>
        ))}
      </div>
    </>
  );
}
