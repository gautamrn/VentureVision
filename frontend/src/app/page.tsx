"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight } from "lucide-react";
import {
  getPitchHistory,
  type PitchHistoryEntry,
} from "@/lib/pitchHistory";

export default function Home() {
  const [pitch, setPitch] = useState("");
  const [mode, setMode] = useState<"quick_check" | "investor_ready">("quick_check");
  const [error, setError] = useState("");
  const [history, setHistory] = useState<PitchHistoryEntry[]>([]);
  const router = useRouter();

  useEffect(() => {
    setHistory(getPitchHistory());
  }, []);

  function handleSubmit(e: React.BaseSyntheticEvent) {
    e.preventDefault();
    const trimmed = pitch.trim();
    if (trimmed.length < 40) {
      setError("Please describe your startup in at least a few sentences.");
      return;
    }
    sessionStorage.setItem("vv_pitch", trimmed);
    sessionStorage.setItem("vv_mode", mode);
    router.push("/analyze");
  }

  function viewPastAnalysis(entry: PitchHistoryEntry) {
    sessionStorage.setItem("vv_view_id", entry.id);
    router.push("/analyze/view");
  }

  return (
    <main className="min-h-screen bg-background flex flex-col items-center justify-center px-6">
      <div className="w-full max-w-2xl">
        <div className="mb-12">
          <h1 className="font-serif text-5xl text-foreground leading-tight mb-4">
            VentureVision
          </h1>
          <p className="font-sans text-2xl text-foreground leading-snug">
            Due diligence, in real time.
          </p>
          <p className="mt-4 text-muted text-base font-sans">
            Describe your startup. Our agents will research the market,
            validate your claims, and write an investment memo.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <textarea
            value={pitch}
            onChange={(e) => {
              setPitch(e.target.value);
              setError("");
            }}
            placeholder="We are building a payments API for unbanked populations on Mars..."
            rows={7}
            className="w-full bg-transparent text-foreground font-sans text-base resize-none outline-none border border-border p-4 placeholder:text-[#C4BFB8]"
          />

          <div className="flex items-center justify-between">
            <p className="text-xs text-muted font-sans">
              {pitch.length} / 300 recommended
            </p>
            {error && (
              <p className="text-sm text-muted font-sans">{error}</p>
            )}
          </div>

          <div className="flex items-center justify-between">
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setMode("quick_check")}
                className={`text-xs font-sans px-3 py-1.5 border ${
                  mode === "quick_check"
                    ? "border-foreground text-foreground"
                    : "border-border text-muted"
                }`}
              >
                Quick Check
              </button>
              <button
                type="button"
                onClick={() => setMode("investor_ready")}
                className={`text-xs font-sans px-3 py-1.5 border ${
                  mode === "investor_ready"
                    ? "border-foreground text-foreground"
                    : "border-border text-muted"
                }`}
              >
                Investor Ready
              </button>
            </div>
            <button
              type="submit"
              className="flex items-center gap-2 text-sm font-sans text-foreground border border-foreground px-5 py-2"
            >
              Analyze pitch
              <ArrowRight size={14} />
            </button>
          </div>
        </form>

        <p className="mt-16 text-xs text-muted font-sans">
          Analysis takes 30–60 seconds. Results are grounded in real web sources.
        </p>

        {history.length > 0 && (
          <div className="mt-12 border-t border-border pt-8">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-sans text-xs uppercase tracking-widest text-muted">
                Past Analyses
              </h2>
              {history.length >= 2 && (
                <button
                  onClick={() => router.push("/compare")}
                  className="text-xs font-sans text-muted hover:text-foreground"
                >
                  Compare
                </button>
              )}
            </div>
            <ul className="space-y-3">
              {history.map((entry) => (
                <li key={entry.id}>
                  <button
                    onClick={() => viewPastAnalysis(entry)}
                    className="w-full text-left flex items-center justify-between border border-border p-3 hover:border-foreground/30"
                  >
                    <div className="min-w-0 flex-1 mr-4">
                      <p className="font-sans text-sm text-foreground truncate">
                        {entry.pitch.slice(0, 80)}{entry.pitch.length > 80 ? "…" : ""}
                      </p>
                      <p className="font-sans text-xs text-muted mt-1">
                        {new Date(entry.date).toLocaleDateString()}
                      </p>
                    </div>
                    <span className="font-serif text-lg text-foreground shrink-0">
                      {entry.pitchScore}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </main>
  );
}
