"use client";

import { useState } from "react";
import { Check, X } from "lucide-react";
import { submitFeedback, type FeedbackSource } from "@/lib/api";
import type { UserVerdict } from "@/lib/types";

interface Props {
  source: FeedbackSource;
  annotationIndex: number;
}

type State = { kind: "idle" } | { kind: "sending" } | { kind: "sent"; verdict: UserVerdict } | { kind: "error"; message: string };

const button =
  "inline-flex items-center justify-center w-5 h-5 border border-border text-muted hover:text-foreground hover:border-foreground/30 disabled:opacity-50 rounded-sm";

export default function VerdictFeedback({ source, annotationIndex }: Props) {
  const [state, setState] = useState<State>({ kind: "idle" });

  async function send(verdict: UserVerdict) {
    setState({ kind: "sending" });
    const result = await submitFeedback(source, annotationIndex, verdict);
    setState(result.ok ? { kind: "sent", verdict } : { kind: "error", message: result.message });
  }

  if (state.kind === "sent") {
    return (
      <p className="font-sans text-[11px] text-muted mt-1 print:hidden">
        Recorded: you marked this verdict {state.verdict}. Reviewed feedback becomes eval candidates.
      </p>
    );
  }

  const disabled = state.kind === "sending";
  return (
    <div className="flex items-center gap-1.5 mt-1 print:hidden">
      <span className="font-sans text-[11px] text-muted">Verdict right?</span>
      <button
        type="button"
        className={button}
        disabled={disabled}
        onClick={() => send("correct")}
        aria-label="This verdict is correct"
        title="Correct. Sends this claim, its evidence and your answer to the eval review queue."
      >
        <Check size={11} />
      </button>
      <button
        type="button"
        className={button}
        disabled={disabled}
        onClick={() => send("wrong")}
        aria-label="This verdict is wrong"
        title="Wrong. Sends this claim, its evidence and your answer to the eval review queue."
      >
        <X size={11} />
      </button>
      {state.kind === "error" && <span className="font-sans text-[11px] text-[#9B2C2C]">{state.message}</span>}
    </div>
  );
}
