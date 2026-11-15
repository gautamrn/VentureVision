"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { RefreshCw } from "lucide-react";
import { MetricsSchema, type Metrics, type RunRecord } from "@/lib/types";
import { NODE_LABELS, formatDuration, formatTokens, formatUsd } from "@/lib/formatRun";
import FeedbackQueue from "@/components/FeedbackQueue";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:3001";
const ADMIN_KEY = process.env.NEXT_PUBLIC_ADMIN_KEY ?? "";
const TIMED_NODES = ["planner", "scout", "critic", "writer"] as const;

function statusColor(status: string): string {
  if (status === "error") return "text-[#9B2C2C]";
  if (status === "cancelled") return "text-[#B08B2D]";
  return "text-[#2D6A4F]";
}

function RecentRunsTable({ runs }: { runs: RunRecord[] }) {
  const cell = "py-2 pr-3 font-sans whitespace-nowrap";
  const head = "font-sans text-left pb-2 pr-3 text-muted font-normal whitespace-nowrap";
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs min-w-[820px]">
        <thead>
          <tr className="border-b border-border">
            <th className={head}>Time</th>
            <th className={head}>Mode</th>
            <th className={head}>Status</th>
            <th className={head}>Score</th>
            <th className={head}>Total</th>
            {TIMED_NODES.map((node) => (
              <th key={node} className={head}>{NODE_LABELS[node]}</th>
            ))}
            <th className={head}>Rounds</th>
            <th className={head}>Tokens (in/out)</th>
            <th className={head}>Searches</th>
            <th className={head}>Cost</th>
          </tr>
        </thead>
        <tbody>
          {runs.map((run) => (
            <tr key={run.runId} className="border-b border-border" title={run.budgetExitReason ?? undefined}>
              <td className={`${cell} text-muted`}>{new Date(run.timestamp * 1000).toLocaleString()}</td>
              <td className={cell}>{run.mode === "pitch_lab" ? "Pitch Lab" : "Scan"}</td>
              <td className={`${cell} ${statusColor(run.status)}`}>{run.status}</td>
              <td className={`${cell} font-serif`}>{run.pitchScore ?? "—"}</td>
              <td className={`${cell} text-muted`}>{formatDuration(run.durationMs)}</td>
              {TIMED_NODES.map((node) => (
                <td key={node} className={`${cell} text-muted`}>
                  {run.nodeMs[node] != null ? formatDuration(run.nodeMs[node]) : "—"}
                </td>
              ))}
              <td className={`${cell} text-muted`}>
                {run.iterations}
                {run.budgetExitReason && <span className="text-[#B08B2D]"> · budget stop</span>}
              </td>
              <td className={`${cell} text-muted`}>
                {run.promptTokens != null && run.completionTokens != null
                  ? `${formatTokens(run.promptTokens)} / ${formatTokens(run.completionTokens)}`
                  : "—"}
              </td>
              <td className={`${cell} text-muted`}>{run.searchCalls ?? "—"}</td>
              <td className={cell}>{run.costUsd != null ? formatUsd(run.costUsd) : "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="border border-border p-4">
      <p className="font-sans text-xs uppercase tracking-widest text-muted mb-1">
        {label}
      </p>
      <p className="font-serif text-2xl text-foreground">{value}</p>
    </div>
  );
}

function ScoreBar({ label, count, total }: { label: string; count: number; total: number }) {
  const pct = total > 0 ? (count / total) * 100 : 0;
  const color =
    label === "High (70+)" ? "#2D6A4F" : label === "Mid (40-69)" ? "#B08B2D" : "#9B2C2C";

  return (
    <div className="flex items-center gap-3">
      <span className="font-sans text-xs text-muted w-24 shrink-0">{label}</span>
      <div className="flex-1 h-3 bg-border">
        <div className="h-full" style={{ width: `${pct}%`, backgroundColor: color }} />
      </div>
      <span className="font-sans text-xs text-muted w-8 text-right">{count}</span>
    </div>
  );
}

export default function AdminPage() {
  const router = useRouter();
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  async function fetchMetrics() {
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/admin/metrics`, {
        headers: ADMIN_KEY ? { "X-Admin-Key": ADMIN_KEY } : {},
      });
      if (res.ok) {
        setMetrics(MetricsSchema.parse(await res.json()));
        setLoadError(null);
      } else {
        setLoadError(res.status === 403 ? "The admin key was rejected (HTTP 403)." : `The backend returned HTTP ${res.status}.`);
      }
    } catch {
      setLoadError(`Could not reach the backend at ${API_URL}.`);
    }
    setLoading(false);
  }

  useEffect(() => {
    fetchMetrics();
  }, []);

  const totalScored =
    metrics
      ? metrics.scoreDistribution.low +
        metrics.scoreDistribution.mid +
        metrics.scoreDistribution.high
      : 0;

  return (
    <main className="min-h-screen bg-background px-6 py-16">
      <div className="w-full max-w-4xl mx-auto">
        <div className="mb-12">
          <button
            onClick={() => router.push("/")}
            className="text-xs font-sans text-muted tracking-widest uppercase mb-8 block"
          >
            &larr; VentureVision
          </button>
          <div className="flex items-center justify-between">
            <div>
              <h1 className="font-serif text-3xl text-foreground mb-1">
                Observability
              </h1>
              <p className="font-sans text-sm text-muted">
                Pipeline metrics and run history
              </p>
            </div>
            <button
              onClick={fetchMetrics}
              disabled={loading}
              className="flex items-center gap-2 text-xs font-sans text-muted border border-border px-3 py-1.5 hover:border-foreground/30"
            >
              <RefreshCw size={12} />
              {loading ? "Loading metrics…" : "Refresh"}
            </button>
          </div>
        </div>

        {loadError && !loading && (
          <p className="font-sans text-sm text-[#9B2C2C] mb-6">{loadError}</p>
        )}

        {metrics && (
          <>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-4">
              <StatCard label="Total Runs" value={metrics.totalRuns} />
              <StatCard label="Errors" value={metrics.totalErrors} />
              <StatCard
                label="Avg Duration"
                value={metrics.avgDurationMs > 0 ? formatDuration(metrics.avgDurationMs) : "—"}
              />
              <StatCard label="Avg Cost" value={metrics.avgCostUsd > 0 ? formatUsd(metrics.avgCostUsd) : "—"} />
              <StatCard label="Total Spend" value={formatUsd(metrics.totalCostUsd)} />
            </div>
            <p className="font-sans text-xs text-muted mb-12">
              Avg per successful run:{" "}
              {TIMED_NODES.map((node) => `${NODE_LABELS[node]} ${formatDuration(metrics.avgNodeMs[node] ?? 0)}`).join(" · ")}{" "}
              · {formatTokens(metrics.avgTokensPerRun)} tokens · score {metrics.avgScore > 0 ? metrics.avgScore : "—"} ·{" "}
              {metrics.budgetExits} budget stops
            </p>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-12">
              <div>
                <h2 className="font-sans text-xs uppercase tracking-widest text-muted mb-4">
                  Score Distribution
                </h2>
                <div className="space-y-3">
                  <ScoreBar label="High (70+)" count={metrics.scoreDistribution.high} total={totalScored} />
                  <ScoreBar label="Mid (40-69)" count={metrics.scoreDistribution.mid} total={totalScored} />
                  <ScoreBar label="Low (&lt;40)" count={metrics.scoreDistribution.low} total={totalScored} />
                </div>
              </div>
              <div>
                <h2 className="font-sans text-xs uppercase tracking-widest text-muted mb-4">
                  Mode Breakdown
                </h2>
                <div className="space-y-2">
                  {Object.entries(metrics.modeBreakdown).map(([mode, count]) => (
                    <div key={mode} className="flex items-center justify-between border border-border p-3">
                      <span className="font-sans text-sm text-foreground">
                        {mode === "pitch_lab" ? "Pitch Lab" : "Market Scan"}
                      </span>
                      <span className="font-serif text-lg text-foreground">{count}</span>
                    </div>
                  ))}
                  {Object.keys(metrics.modeBreakdown).length === 0 && (
                    <p className="font-sans text-sm text-muted">No runs yet</p>
                  )}
                </div>
                <div className="mt-4 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-sans text-xs text-muted">Avg Iterations</span>
                    <span className="font-sans text-sm text-foreground">{metrics.avgIterations}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="font-sans text-xs text-muted">Avg Evidence</span>
                    <span className="font-sans text-sm text-foreground">{metrics.avgEvidence} sources</span>
                  </div>
                </div>
              </div>
            </div>

            <div>
              <h2 className="font-sans text-xs uppercase tracking-widest text-muted mb-4">
                Recent Runs
              </h2>
              {metrics.recentRuns.length === 0 ? (
                <p className="font-sans text-sm text-muted">No runs recorded yet.</p>
              ) : (
                <RecentRunsTable runs={metrics.recentRuns} />
              )}
            </div>
          </>
        )}

        <FeedbackQueue adminKey={ADMIN_KEY} />
      </div>
    </main>
  );
}
