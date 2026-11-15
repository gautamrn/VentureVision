"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowRight, X } from "lucide-react";
import { DEMO_SAMPLES } from "@/data/demo/samples";
import {
  getPitchHistory,
  deletePitch,
  type PitchHistoryEntry,
} from "@/lib/pitchHistory";

export default function Home() {
  const [pitch, setPitch] = useState("");
  const [mode, setMode] = useState<"market_scan" | "pitch_lab">("market_scan");
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
      setError("Minimum 40 characters.");
      return;
    }
    if (trimmed.length > 5000) {
      setError("Maximum 5,000 characters.");
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

  function handleDelete(e: React.MouseEvent, id: string) {
    e.stopPropagation();
    deletePitch(id);
    setHistory(getPitchHistory());
  }

  return (
    <main className="min-h-screen bg-background flex flex-col items-center justify-center px-6 py-16">
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

        <section className="mb-14" aria-labelledby="demo-heading">
          <div className="flex items-baseline justify-between mb-3">
            <h2 id="demo-heading" className="font-sans text-xs uppercase tracking-widest text-foreground">
              Try the demo
            </h2>
            <p className="font-sans text-xs text-muted">No API key, no sign-up</p>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {DEMO_SAMPLES.map((sample) => (
              <Link
                key={sample.id}
                href={`/demo/${sample.id}`}
                className="flex flex-col border border-border p-3 rounded-sm hover:border-foreground"
              >
                <span className="font-sans text-[11px] uppercase tracking-widest text-muted">{sample.category}</span>
                <span className="font-serif text-lg text-foreground mt-1">{sample.title}</span>
                <span className="font-sans text-xs text-muted mt-1 leading-snug">{sample.tagline}</span>
                <span className="font-sans text-xs text-foreground mt-3 flex items-center gap-1">
                  View memo <ArrowRight size={12} />
                </span>
              </Link>
            ))}
          </div>
          <p className="font-sans text-xs text-muted mt-3">
            Recorded runs of the real pipeline on three sample one-pagers, replayed in your browser.
          </p>
        </section>

        <div id="live" className="flex items-baseline justify-between mb-3 scroll-mt-8">
          <h2 className="font-sans text-xs uppercase tracking-widest text-foreground">Live mode: analyze your pitch</h2>
          <p className="font-sans text-xs text-muted">5 runs per hour per visitor</p>
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
            maxLength={5000}
            className="w-full bg-transparent text-foreground font-sans text-base resize-none outline-none border border-border p-4 placeholder:text-[#C4BFB8]"
          />

          <div className="flex items-center justify-between">
            <p className={`text-xs font-sans ${
              pitch.length > 5000 ? "text-[#9B2C2C]" : pitch.length < 40 ? "text-muted" : "text-[#2D6A4F]"
            }`}>
              {pitch.length} / 5,000 · at least 40 chars
            </p>
            {error && (
              <p className="text-sm text-[#9B2C2C] font-sans">{error}</p>
            )}
          </div>

          <div className="flex items-center justify-between">
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setMode("market_scan")}
                className={`text-xs font-sans px-3 py-1.5 border cursor-pointer active:scale-95 transition-transform ${
                  mode === "market_scan"
                    ? "border-foreground text-foreground bg-foreground/5"
                    : "border-border text-muted hover:border-foreground/30 hover:text-foreground"
                }`}
              >
                Market Scan
              </button>
              <button
                type="button"
                onClick={() => setMode("pitch_lab")}
                className={`text-xs font-sans px-3 py-1.5 border cursor-pointer active:scale-95 transition-transform ${
                  mode === "pitch_lab"
                    ? "border-foreground text-foreground bg-foreground/5"
                    : "border-border text-muted hover:border-foreground/30 hover:text-foreground"
                }`}
              >
                Pitch Lab
              </button>
            </div>
            <button
              type="submit"
              className="flex items-center gap-2 text-sm font-sans text-foreground border border-foreground px-5 py-2 cursor-pointer hover:bg-foreground/5 active:scale-95 transition-transform"
            >
              Analyze pitch
              <ArrowRight size={14} />
            </button>
          </div>
        </form>

        <div className="mt-16">
          <p className="text-xs text-muted font-sans">
            Analysis takes 30–60 seconds. Results are grounded in real web sources.
          </p>
          <Link href="/evals" className="font-sans text-xs text-foreground hover:underline mt-2 inline-block">
            How often are the verdicts right? See the evals &rarr;
          </Link>
        </div>

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
                  <div
                    role="button"
                    tabIndex={0}
                    onClick={() => viewPastAnalysis(entry)}
                    onKeyDown={(e) => { if (e.key === "Enter") viewPastAnalysis(entry); }}
                    className="w-full text-left flex items-center justify-between border border-border p-3 hover:border-foreground/30 cursor-pointer"
                  >
                    <div className="min-w-0 flex-1 mr-4">
                      <p className="font-sans text-sm text-foreground truncate">
                        {entry.pitch.slice(0, 80)}{entry.pitch.length > 80 ? "…" : ""}
                      </p>
                      <p className="font-sans text-xs text-muted mt-1">
                        {new Date(entry.date).toLocaleDateString()}
                      </p>
                    </div>
                    <div className="flex items-center gap-3 shrink-0">
                      <span className="font-serif text-lg text-foreground">
                        {entry.pitchScore}
                      </span>
                      <button
                        onClick={(e) => handleDelete(e, entry.id)}
                        className="text-muted hover:text-foreground active:scale-90 transition-transform"
                      >
                        <X size={14} />
                      </button>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </main>
  );
}
