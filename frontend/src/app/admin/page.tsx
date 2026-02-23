"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { RefreshCw } from "lucide-react";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:3001";
const ADMIN_KEY = process.env.NEXT_PUBLIC_ADMIN_KEY ?? "";

interface RunRecord {
  timestamp: number;
  durationMs: number;
  mode: string;
  pitchScore: number | null;
  iterations: number;
  evidenceCount: number;
  status: string;
}

interface Metrics {
  totalRuns: number;
  totalErrors: number;
  avgDurationMs: number;
  avgScore: number;
  avgIterations: number;
  avgEvidence: number;
  modeBreakdown: Record<string, number>;
  scoreDistribution: { low: number; mid: number; high: number };
  recentRuns: RunRecord[];
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

  async function fetchMetrics() {
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/admin/metrics`, {
        headers: ADMIN_KEY ? { "X-Admin-Key": ADMIN_KEY } : {},
      });
      if (res.ok) {
        setMetrics(await res.json());
      }
    } catch {
      setMetrics(null);
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
              <RefreshCw size={12} className={loading ? "animate-spin" : ""} />
              Refresh
            </button>
          </div>
        </div>

        {!metrics && !loading && (
          <p className="font-sans text-sm text-muted">
            Could not connect to the backend.
          </p>
        )}

        {metrics && (
          <>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-12">
              <StatCard label="Total Runs" value={metrics.totalRuns} />
              <StatCard label="Errors" value={metrics.totalErrors} />
              <StatCard
                label="Avg Duration"
                value={metrics.avgDurationMs > 0 ? `${(metrics.avgDurationMs / 1000).toFixed(1)}s` : "—"}
              />
              <StatCard
                label="Avg Score"
                value={metrics.avgScore > 0 ? metrics.avgScore : "—"}
              />
            </div>

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
                <div className="overflow-x-auto">
                  <table className="w-full text-sm min-w-[600px]">
                    <thead>
                      <tr className="border-b border-border">
                        <th className="font-sans text-left pb-2 text-muted font-normal">Time</th>
                        <th className="font-sans text-left pb-2 text-muted font-normal">Mode</th>
                        <th className="font-sans text-left pb-2 text-muted font-normal">Score</th>
                        <th className="font-sans text-left pb-2 text-muted font-normal">Duration</th>
                        <th className="font-sans text-left pb-2 text-muted font-normal">Iterations</th>
                        <th className="font-sans text-left pb-2 text-muted font-normal">Evidence</th>
                        <th className="font-sans text-left pb-2 text-muted font-normal">Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {metrics.recentRuns.map((run, i) => (
                        <tr key={i} className="border-b border-border">
                          <td className="py-3 font-sans text-muted">
                            {new Date(run.timestamp * 1000).toLocaleString()}
                          </td>
                          <td className="py-3 font-sans">
                            {run.mode === "pitch_lab" ? "Pitch Lab" : "Scan"}
                          </td>
                          <td className="py-3 font-serif">
                            {run.pitchScore ?? "—"}
                          </td>
                          <td className="py-3 font-sans text-muted">
                            {(run.durationMs / 1000).toFixed(1)}s
                          </td>
                          <td className="py-3 font-sans text-muted">{run.iterations}</td>
                          <td className="py-3 font-sans text-muted">{run.evidenceCount}</td>
                          <td className="py-3 font-sans">
                            <span className={run.status === "error" ? "text-[#9B2C2C]" : "text-[#2D6A4F]"}>
                              {run.status}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </main>
  );
}
