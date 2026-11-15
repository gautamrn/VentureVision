"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import AgentStatus, { type Status } from "./AgentStatus";
import PitchScore from "./PitchScore";
import MemoDocument from "./MemoDocument";
import { statusForEvent } from "@/lib/agentEvents";
import type { MemoOutput } from "@/lib/types";
import type { ParsedDemoRun } from "@/data/demo/loadDemoRun";

const REPLAY_TARGET_MS = 9000;

export default function DemoReplay({ run }: { run: ParsedDemoRun }) {
  const [status, setStatus] = useState<Status>({ phase: "planner" });
  const [memo, setMemo] = useState<MemoOutput | null>(null);
  const timers = useRef<ReturnType<typeof setTimeout>[]>([]);

  const speedup = Math.max(1, run.durationMs / REPLAY_TARGET_MS);

  useEffect(() => {
    timers.current = run.events.map(({ atMs, event }) =>
      setTimeout(() => {
        setStatus(statusForEvent(event));
        if (event.type === "citation_audit") setMemo(event.data.memo);
      }, atMs / speedup)
    );
    return () => timers.current.forEach(clearTimeout);
  }, [run, speedup]);

  function skipToMemo() {
    timers.current.forEach(clearTimeout);
    setStatus({ phase: "done" });
    setMemo(run.memo);
  }

  return (
    <main className="min-h-screen bg-background px-6 py-16">
      <div className="w-full max-w-2xl mx-auto">
        <div className="mb-10">
          <Link href="/" className="text-xs font-sans text-muted tracking-widest uppercase mb-8 block">
            &larr; VentureVision
          </Link>
          <div className="flex items-center gap-3 mb-2">
            <p className="font-sans text-xs uppercase tracking-widest text-muted">Investment Memo</p>
            <span className="font-sans text-xs px-2 py-0.5 border border-border text-muted">
              {run.mode === "pitch_lab" ? "Pitch Lab" : "Market Scan"}
            </span>
            <span className="font-sans text-xs text-muted">{run.category}</span>
          </div>
          <p className="font-serif text-xl text-foreground leading-snug">
            {run.title}: {run.tagline}
          </p>
          <p className="font-sans text-xs text-muted mt-3 leading-relaxed">
            Replaying a real pipeline run recorded {run.recordedAt.slice(0, 10)} (
            {Math.round(run.durationMs / 1000)}s of live web research, shown at {speedup.toFixed(0)}× speed). No API
            keys, no API calls.
          </p>
        </div>

        {!memo && (
          <div className="flex items-start justify-between gap-6">
            <div className="flex-1">
              <AgentStatus status={status} />
            </div>
            <button
              type="button"
              onClick={skipToMemo}
              className="font-sans text-xs text-muted hover:text-foreground border border-border px-3 py-1.5 rounded-sm shrink-0"
            >
              Skip to memo
            </button>
          </div>
        )}

        {memo ? (
          <>
            <PitchScore pitchScore={memo.pitch_score} subscores={memo.subscores} />
            <MemoDocument memo={memo} pitch={run.pitch} source={{ kind: "demo", recordedAt: run.recordedAt }} />
            <div className="border-t border-border pt-6 mt-4">
              <Link href="/#live" className="font-sans text-sm text-foreground hover:underline">
                Run your own pitch live &rarr;
              </Link>
            </div>
          </>
        ) : (
          <div className="space-y-4">
            <div className="h-4 w-3/4 bg-border" />
            <div className="h-4 w-full bg-border" />
            <div className="h-4 w-5/6 bg-border" />
          </div>
        )}
      </div>
    </main>
  );
}
