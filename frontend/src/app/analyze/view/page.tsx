"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import PitchScore from "@/components/PitchScore";
import MemoDocument from "@/components/MemoDocument";
import { getPitchById, type PitchHistoryEntry } from "@/lib/pitchHistory";

export default function ViewAnalysisPage() {
  const router = useRouter();
  const [entry, setEntry] = useState<PitchHistoryEntry | null>(null);

  useEffect(() => {
    const id = sessionStorage.getItem("vv_view_id");
    if (!id) {
      router.replace("/");
      return;
    }
    const found = getPitchById(id);
    if (!found) {
      router.replace("/");
      return;
    }
    setEntry(found);
  }, [router]);

  if (!entry) return null;

  return (
    <main className="min-h-screen bg-background px-6 py-16">
      <div className="w-full max-w-2xl mx-auto">
        <div className="mb-12">
          <button
            onClick={() => router.push("/")}
            className="text-xs font-sans text-muted tracking-widest uppercase mb-8 block"
          >
            &larr; VentureVision
          </button>
          <p className="font-sans text-xs uppercase tracking-widest text-muted mb-2">
            Past Analysis &middot; {new Date(entry.date).toLocaleDateString()}
          </p>
          <p className="font-serif text-xl text-foreground leading-snug">
            {entry.pitch.slice(0, 80)}{entry.pitch.length > 80 ? "\u2026" : ""}
          </p>
        </div>

        <PitchScore
          pitchScore={entry.memo.pitch_score}
          subscores={entry.memo.subscores}
        />
        <MemoDocument memo={entry.memo} pitch={entry.pitch} />
      </div>
    </main>
  );
}
