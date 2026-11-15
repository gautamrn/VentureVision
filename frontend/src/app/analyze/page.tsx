"use client";

import { useEffect, useReducer, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { cancelRun, retryRun, startAnalysis } from "@/lib/api";
import AgentTimeline from "@/components/AgentTimeline";
import PitchScore from "@/components/PitchScore";
import MemoDocument from "@/components/MemoDocument";
import type { AgentEvent } from "@/lib/types";
import { savePitchResult } from "@/lib/pitchHistory";
import { initialTimeline, timelineReducer } from "@/lib/timeline";

const CANCEL_CONFIRM_TIMEOUT_MS = 30_000;

export default function AnalyzePage() {
  const router = useRouter();
  const [timeline, dispatch] = useReducer(timelineReducer, undefined, initialTimeline);
  const [pitch, setPitch] = useState<string>("");
  const [mode, setMode] = useState<string>("market_scan");
  const hasStarted = useRef(false);
  const abortRef = useRef<AbortController | null>(null);
  const pitchRef = useRef({ pitch: "", mode: "market_scan" });
  const unmountTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  function handleEvent(event: AgentEvent) {
    dispatch({ type: "event", event, at: Date.now() });
    if (event.type === "citation_audit") {
      savePitchResult(pitchRef.current.pitch, event.data.memo, pitchRef.current.mode);
    }
  }

  function consume(stream: (signal: AbortSignal) => Promise<void>) {
    const controller = new AbortController();
    abortRef.current = controller;
    stream(controller.signal)
      .catch(() => undefined)
      .finally(() => {
        if (abortRef.current === controller) abortRef.current = null;
        dispatch({ type: "streamEnded" });
      });
  }

  useEffect(() => {
    // Leaving the page closes the stream, which the server treats as a cancel. The abort is
    // deferred one tick so React's development double-mount doesn't cancel the real run.
    const closeOnUnmount = () => {
      unmountTimer.current = setTimeout(() => abortRef.current?.abort(), 0);
    };
    if (unmountTimer.current) {
      clearTimeout(unmountTimer.current);
      unmountTimer.current = null;
    }
    if (hasStarted.current) return closeOnUnmount;
    hasStarted.current = true;

    const stored = sessionStorage.getItem("vv_pitch");
    if (!stored) {
      router.replace("/");
      return;
    }
    const storedMode = sessionStorage.getItem("vv_mode") ?? "market_scan";
    pitchRef.current = { pitch: stored, mode: storedMode };
    setPitch(stored);
    setMode(storedMode);
    dispatch({ type: "started", at: Date.now() });
    consume((signal) => startAnalysis(stored, storedMode, handleEvent, signal));
    return closeOnUnmount;
  }, [router]);

  async function handleCancel() {
    dispatch({ type: "cancelRequested" });
    const stream = abortRef.current;
    const accepted = timeline.runId ? await cancelRun(timeline.runId) : false;
    if (!accepted) {
      // No run id yet, or the server no longer knows the run: closing the stream is the cancel signal.
      stream?.abort();
      return;
    }
    setTimeout(() => {
      if (abortRef.current === stream) stream?.abort();
    }, CANCEL_CONFIRM_TIMEOUT_MS);
  }

  function handleRetry() {
    if (!timeline.runId) return;
    const runId = timeline.runId;
    dispatch({ type: "retryStarted", at: Date.now() });
    consume((signal) => retryRun(runId, handleEvent, signal));
  }

  function leave() {
    abortRef.current?.abort();
    router.push("/");
  }

  const memo = timeline.memo;

  return (
    <main className="min-h-screen bg-background px-6 py-16">
      <div className="w-full max-w-2xl mx-auto">
        <div className="mb-12">
          <button onClick={leave} className="text-xs font-sans text-muted tracking-widest uppercase mb-8 block">
            ← VentureVision
          </button>
          <div className="flex items-center gap-3 mb-2">
            <p className="font-sans text-xs uppercase tracking-widest text-muted">Investment Memo</p>
            <span className="font-sans text-xs px-2 py-0.5 border border-border text-muted">
              {mode === "pitch_lab" ? "Pitch Lab" : "Market Scan"}
            </span>
          </div>
          {pitch && (
            <p className="font-serif text-xl text-foreground leading-snug">
              {pitch.slice(0, 80)}
              {pitch.length > 80 ? "…" : ""}
            </p>
          )}
        </div>

        <AgentTimeline timeline={timeline} onCancel={handleCancel} onRetry={handleRetry} onStartOver={leave} />

        {memo && (
          <>
            <PitchScore pitchScore={memo.pitch_score} subscores={memo.subscores} />
            <MemoDocument memo={memo} pitch={pitch} source={{ kind: "live" }} />
          </>
        )}
      </div>
    </main>
  );
}
