"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { streamAnalysis } from "@/lib/api";
import AgentStatus, { type Status } from "@/components/AgentStatus";
import PitchScore from "@/components/PitchScore";
import MemoDocument from "@/components/MemoDocument";
import type { MemoOutput } from "@/lib/types";
import { savePitchResult } from "@/lib/pitchHistory";

export default function AnalyzePage() {
  const router = useRouter();
  const [status, setStatus] = useState<Status>({ phase: "planner" });
  const [memo, setMemo] = useState<MemoOutput | null>(null);
  const [pitch, setPitch] = useState<string>("");
  const [mode, setMode] = useState<string>("market_scan");
  const hasStarted = useRef(false);

  useEffect(() => {
    if (hasStarted.current) return;
    hasStarted.current = true;

    const stored = sessionStorage.getItem("vv_pitch");
    if (!stored) {
      router.replace("/");
      return;
    }
    setPitch(stored);
    const storedMode = sessionStorage.getItem("vv_mode") ?? "market_scan";
    setMode(storedMode);

    streamAnalysis(
      stored,
      storedMode,
      (event) => {
        if (event.type === "planner") {
          setStatus({ phase: "scout", evidenceCount: 0 });
        }
        if (event.type === "scout") {
          setStatus({ phase: "scout", evidenceCount: event.data.evidenceCount });
        }
        if (event.type === "critic") {
          if (event.data.isValidated) {
            setStatus({ phase: "writer" });
          } else {
            setStatus({
              phase: "critic",
              iteration: event.data.iteration,
              coverageScore: event.data.coverageScore,
              feedback: event.data.feedback,
            });
          }
        }
        if (event.type === "writer" && event.data.memoReady) {
          setStatus({ phase: "audit" });
        }
        if (event.type === "citation_audit") {
          setMemo(event.data.memo);
          setStatus({ phase: "done" });
          savePitchResult(stored, event.data.memo, storedMode);
        }
        if (event.type === "writer" && !event.data.memoReady) {
          setStatus({ phase: "error", message: "Analysis failed. Please try again." });
        }
        if (event.type === "error") {
          setStatus({ phase: "error", message: event.data.message });
        }
      },
      () => {
        setStatus((prev) => (prev.phase !== "error" ? { phase: "done" } : prev));
      }
    );
  }, [router]);

  return (
    <main className="min-h-screen bg-background px-6 py-16">
      <div className="w-full max-w-2xl mx-auto">
        <div className="mb-12">
          <button
            onClick={() => router.push("/")}
            className="text-xs font-sans text-muted tracking-widest uppercase mb-8 block"
          >
            ← VentureVision
          </button>
          <div className="flex items-center gap-3 mb-2">
            <p className="font-sans text-xs uppercase tracking-widest text-muted">
              Investment Memo
            </p>
            <span className="font-sans text-xs px-2 py-0.5 border border-border text-muted">
              {mode === "pitch_lab" ? "Pitch Lab" : "Market Scan"}
            </span>
          </div>
          {pitch && (
            <p className="font-serif text-xl text-foreground leading-snug">
              {pitch.slice(0, 80)}{pitch.length > 80 ? "…" : ""}
            </p>
          )}
        </div>

        <AgentStatus status={status} />

        {memo ? (
          <>
            <PitchScore
              pitchScore={memo.pitch_score}
              subscores={memo.subscores}
            />
            <MemoDocument memo={memo} pitch={pitch} />
          </>
        ) : status.phase !== "error" ? (
          <div className="space-y-4">
            <div className="h-4 w-3/4 bg-border" />
            <div className="h-4 w-full bg-border" />
            <div className="h-4 w-5/6 bg-border" />
          </div>
        ) : null}
      </div>
    </main>
  );
}
