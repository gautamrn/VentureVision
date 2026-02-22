"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight } from "lucide-react";

export default function Home() {
  const [pitch, setPitch] = useState("");
  const [error, setError] = useState("");
  const router = useRouter();

  function handleSubmit(e: React.BaseSyntheticEvent) {
    e.preventDefault();
    const trimmed = pitch.trim();
    if (trimmed.length < 40) {
      setError("Please describe your startup in at least a few sentences.");
      return;
    }
    sessionStorage.setItem("vv_pitch", trimmed);
    router.push("/analyze");
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

          {error && (
            <p className="text-sm text-muted font-sans">{error}</p>
          )}

          <div className="flex justify-end">
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
      </div>
    </main>
  );
}
