import type { RunTelemetry } from "@/lib/types";
import { NODE_LABELS, formatDuration, formatTokens, formatUsd } from "@/lib/formatRun";

export default function RunFooter({ telemetry }: { telemetry: RunTelemetry }) {
  const searchNote =
    telemetry.failed_searches > 0
      ? `${telemetry.search_calls} web searches (${telemetry.failed_searches} failed)`
      : `${telemetry.search_calls} web searches`;

  return (
    <footer className="mt-12 pt-4 border-t border-border font-sans text-xs text-muted">
      <p className="text-foreground">
        This analysis: {telemetry.agent_count} agents, {formatDuration(telemetry.duration_ms)}, ~
        {formatUsd(telemetry.total_cost_usd)}
      </p>
      <p className="mt-1">
        {telemetry.llm_calls} model calls · {formatTokens(telemetry.prompt_tokens)} prompt +{" "}
        {formatTokens(telemetry.completion_tokens)} completion tokens ({formatUsd(telemetry.llm_cost_usd)}) ·{" "}
        {searchNote} ({formatUsd(telemetry.search_cost_usd)})
      </p>
      <p className="mt-1">
        {telemetry.nodes
          .map((n) => `${NODE_LABELS[n.node] ?? n.node} ${formatDuration(n.total_ms)}${n.runs > 1 ? ` ×${n.runs}` : ""}`)
          .join(" · ")}
      </p>
      {telemetry.budget_exit_reason && <p className="mt-1 text-[#B08B2D]">{telemetry.budget_exit_reason}</p>}
      <p className="mt-1">
        Measured during the run; costs use list prices as of {telemetry.pricing_as_of}. Budget{" "}
        {formatUsd(telemetry.budget_usd)} per run.
      </p>
    </footer>
  );
}
