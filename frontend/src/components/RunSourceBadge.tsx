import type { RunSource } from "@/lib/types";

export default function RunSourceBadge({ source }: { source: RunSource }) {
  if (source.kind === "demo") {
    return (
      <span
        className="font-sans text-[11px] uppercase tracking-widest px-2 py-0.5 bg-foreground text-background rounded-sm shrink-0"
        title={`Recorded from a real pipeline run on ${source.recordedAt.slice(0, 10)}. No API calls are made when you view it.`}
      >
        Demo data
      </span>
    );
  }
  return (
    <span className="font-sans text-[11px] uppercase tracking-widest px-2 py-0.5 border border-foreground text-foreground rounded-sm shrink-0">
      Live run
    </span>
  );
}
