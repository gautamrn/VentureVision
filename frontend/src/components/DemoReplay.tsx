"use client";

import { useEffect, useReducer, useRef } from "react";
import Link from "next/link";
import AgentTimeline from "./AgentTimeline";
import PitchScore from "./PitchScore";
import MemoDocument from "./MemoDocument";
import { initialTimeline, timelineReducer } from "@/lib/timeline";
import type { ParsedDemoRun } from "@/data/demo/loadDemoRun";

const REPLAY_TARGET_MS = 9000;

export default function DemoReplay({ run }: { run: ParsedDemoRun }) {
  const [timeline, dispatch] = useReducer(timelineReducer, undefined, initialTimeline);
  const timers = useRef<ReturnType<typeof setTimeout>[]>([]);

  const speedup = Math.max(1, run.durationMs / REPLAY_TARGET_MS);

  useEffect(() => {
    dispatch({ type: "started", at: Date.now() });
    timers.current = run.events.map(({ atMs, event }) =>
      setTimeout(() => dispatch({ type: "event", event, at: Date.now() }), atMs / speedup)
    );
    return () => timers.current.forEach(clearTimeout);
  }, [run, speedup]);

  function skipToMemo() {
    timers.current.forEach(clearTimeout);
    const at = Date.now();
    for (const { event } of run.events) dispatch({ type: "event", event, at });
  }

  const memo = timeline.memo;

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
          <div className="flex justify-end mb-3">
            <button
              type="button"
              onClick={skipToMemo}
              className="font-sans text-xs text-muted hover:text-foreground border border-border px-3 py-1.5 rounded-sm"
            >
              Skip to memo
            </button>
          </div>
        )}

        <AgentTimeline timeline={timeline} />

        {memo && (
          <>
            <PitchScore pitchScore={memo.pitch_score} subscores={memo.subscores} />
            <MemoDocument memo={memo} pitch={run.pitch} source={{ kind: "demo", recordedAt: run.recordedAt }} />
            <div className="border-t border-border pt-6 mt-4">
              <Link href="/#live" className="font-sans text-sm text-foreground hover:underline">
                Run your own pitch live &rarr;
              </Link>
            </div>
          </>
        )}
      </div>
    </main>
  );
}
