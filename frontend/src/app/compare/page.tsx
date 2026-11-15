"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import PitchScore from "@/components/PitchScore";
import MemoDocument from "@/components/MemoDocument";
import {
  getPitchHistory,
  type PitchHistoryEntry,
} from "@/lib/pitchHistory";

export default function ComparePage() {
  const router = useRouter();
  const [history, setHistory] = useState<PitchHistoryEntry[]>([]);
  const [leftId, setLeftId] = useState<string | null>(null);
  const [rightId, setRightId] = useState<string | null>(null);

  useEffect(() => {
    const entries = getPitchHistory();
    if (entries.length < 2) {
      router.replace("/");
      return;
    }
    setHistory(entries);
    setLeftId(entries[0].id);
    setRightId(entries[1].id);
  }, [router]);

  const left = history.find((e) => e.id === leftId) ?? null;
  const right = history.find((e) => e.id === rightId) ?? null;

  if (history.length < 2) return null;

  return (
    <main className="min-h-screen bg-background px-6 py-16">
      <div className="w-full max-w-6xl mx-auto">
        <div className="mb-12">
          <button
            onClick={() => router.push("/")}
            className="text-xs font-sans text-muted tracking-widest uppercase mb-8 block"
          >
            &larr; VentureVision
          </button>
          <h1 className="font-serif text-3xl text-foreground mb-2">
            Compare Analyses
          </h1>
          <p className="font-sans text-sm text-muted">
            Select two past analyses to compare side by side.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-12">
          <div>
            <label className="font-sans text-xs uppercase tracking-widest text-muted mb-2 block">
              Left
            </label>
            <select
              value={leftId ?? ""}
              onChange={(e) => setLeftId(e.target.value)}
              className="w-full bg-transparent border border-border p-2 font-sans text-sm text-foreground"
            >
              {history.map((entry) => (
                <option key={entry.id} value={entry.id}>
                  {entry.pitch.slice(0, 60)}… — {entry.pitchScore}/100
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="font-sans text-xs uppercase tracking-widest text-muted mb-2 block">
              Right
            </label>
            <select
              value={rightId ?? ""}
              onChange={(e) => setRightId(e.target.value)}
              className="w-full bg-transparent border border-border p-2 font-sans text-sm text-foreground"
            >
              {history.map((entry) => (
                <option key={entry.id} value={entry.id}>
                  {entry.pitch.slice(0, 60)}… — {entry.pitchScore}/100
                </option>
              ))}
            </select>
          </div>
        </div>

        {left && right && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            <div className="border-r border-border pr-8">
              <PitchScore
                pitchScore={left.memo.pitch_score}
                subscores={left.memo.subscores}
              />
              <MemoDocument memo={left.memo} pitch={left.pitch} source={{ kind: "live" }} />
            </div>
            <div>
              <PitchScore
                pitchScore={right.memo.pitch_score}
                subscores={right.memo.subscores}
              />
              <MemoDocument memo={right.memo} pitch={right.pitch} source={{ kind: "live" }} />
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
