"use client";

import { useState } from "react";
import { Check, Clipboard, FileDown, Link2 } from "lucide-react";
import { createShare, type ShareableMemo } from "@/lib/api";
import type { MemoOutput, ShareSeal } from "@/lib/types";

interface MemoForSharing {
  pitch: string;
  mode: string;
  memo: MemoOutput;
  seal?: ShareSeal | null;
}

interface Props {
  kind: "memo" | "compare";
  memos: MemoForSharing[];
  /** Hide the share-link control, e.g. for demo memos that are already public. */
  printOnly?: boolean;
}

const button =
  "inline-flex items-center gap-1.5 border border-border px-3 py-1.5 rounded-sm text-xs text-foreground hover:border-foreground disabled:text-muted disabled:hover:border-border";

type ShareState = { kind: "idle" } | { kind: "creating" } | { kind: "created"; url: string } | { kind: "failed"; message: string };

export default function ShareActions({ kind, memos, printOnly = false }: Props) {
  const [share, setShare] = useState<ShareState>({ kind: "idle" });
  const [copied, setCopied] = useState(false);
  const sealed = memos.every((m) => m.seal);

  async function handleShare() {
    setShare({ kind: "creating" });
    const payload = memos.map((m) => ({ pitch: m.pitch, mode: m.mode, memo: m.memo, seal: m.seal })) as ShareableMemo[];
    const result = await createShare(kind, payload);
    setShare(
      result.ok
        ? { kind: "created", url: `${window.location.origin}/share/${result.shareId}` }
        : { kind: "failed", message: result.message }
    );
  }

  async function handleCopy(url: string) {
    await navigator.clipboard.writeText(url);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div className="font-sans text-xs mb-8 print:hidden">
      <div className="flex flex-wrap items-center gap-3">
        <button type="button" onClick={() => window.print()} className={button}>
          <FileDown size={12} /> Download PDF
        </button>
        {!printOnly && share.kind !== "created" && (
          <button type="button" onClick={handleShare} disabled={!sealed || share.kind === "creating"} className={button}>
            <Link2 size={12} />
            {share.kind === "creating" ? "Creating link…" : "Create share link"}
          </button>
        )}
      </div>

      {!printOnly && !sealed && (
        <p className="text-muted mt-2">
          {kind === "compare" ? "One of these analyses was" : "This analysis was"} saved before share links existed, so the
          server can&apos;t confirm it generated it. Run it again to share it.
        </p>
      )}
      {share.kind === "failed" && <p className="text-[#9B2C2C] mt-2">Couldn&apos;t create a share link: {share.message}</p>}
      {share.kind === "created" && (
        <div className="mt-3 border border-border p-3 space-y-2">
          <div className="flex items-center gap-2">
            <input
              readOnly
              value={share.url}
              onFocus={(e) => e.currentTarget.select()}
              aria-label="Share link"
              className="flex-1 min-w-0 bg-transparent border border-border px-2 py-1 text-foreground rounded-sm"
            />
            <button type="button" onClick={() => handleCopy(share.url)} className={button}>
              {copied ? <Check size={12} /> : <Clipboard size={12} />}
              {copied ? "Copied" : "Copy"}
            </button>
          </div>
          <p className="text-muted">
            Anyone with this link can read the {kind === "compare" ? "comparison" : "memo"}, including the pitch text. No
            sign-in, and nothing about visitors is recorded.
          </p>
        </div>
      )}
    </div>
  );
}
