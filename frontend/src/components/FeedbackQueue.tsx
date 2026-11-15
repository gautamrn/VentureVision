"use client";

import { useEffect, useState } from "react";
import { ExternalLink } from "lucide-react";
import { fetchFeedback, reviewFeedback } from "@/lib/api";
import { EvalLabelSchema, type EvalLabel, type FeedbackList, type FeedbackRecord } from "@/lib/types";

const VERDICT_LABELS: Record<string, string> = {
  strong: "Supported",
  contradicted: "Contradicted",
  needs_research: "Needs research",
  unsubstantiated: "Unsubstantiated",
  vague: "Vague",
  weak_claim: "Weak claim",
};
const HIGH_VALUE = new Set(["strong", "contradicted"]);
const EXPORT_COMMAND = ".venv\\Scripts\\python.exe -m scripts.exportFeedback";

type Loaded = { ok: true; data: FeedbackList } | { ok: false; message: string };

function ReviewControls({ record, adminKey, onReviewed }: { record: FeedbackRecord; adminKey: string; onReviewed: () => void }) {
  const [goldLabel, setGoldLabel] = useState<EvalLabel | "">("");
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function review(status: "accepted" | "rejected") {
    setBusy(true);
    const result = await reviewFeedback(adminKey, record.feedback_id, {
      status,
      ...(status === "accepted" && goldLabel ? { gold_label: goldLabel } : {}),
      note,
    });
    setBusy(false);
    if (result.ok) onReviewed();
    else setError(result.message);
  }

  return (
    <div className="flex flex-wrap items-center gap-2 mt-2">
      <select
        value={goldLabel}
        onChange={(e) => setGoldLabel(EvalLabelSchema.safeParse(e.target.value).data ?? "")}
        className="bg-transparent border border-border px-2 py-1 font-sans text-xs text-foreground"
        aria-label="Correct label"
      >
        <option value="">Correct label…</option>
        {EvalLabelSchema.options.map((label) => (
          <option key={label} value={label}>{label}</option>
        ))}
      </select>
      <input
        value={note}
        onChange={(e) => setNote(e.target.value)}
        maxLength={1000}
        placeholder="Reviewer note (why)"
        className="flex-1 min-w-[180px] bg-transparent border border-border px-2 py-1 font-sans text-xs text-foreground"
      />
      <button
        type="button"
        disabled={busy || !goldLabel}
        onClick={() => review("accepted")}
        className="border border-border px-2 py-1 font-sans text-xs text-foreground hover:border-foreground/30 disabled:opacity-50"
        title={goldLabel ? "Accept as an eval candidate with this label" : "Pick the correct label first"}
      >
        Accept
      </button>
      <button
        type="button"
        disabled={busy}
        onClick={() => review("rejected")}
        className="border border-border px-2 py-1 font-sans text-xs text-muted hover:border-foreground/30 disabled:opacity-50"
      >
        Reject
      </button>
      {error && <span className="font-sans text-xs text-[#9B2C2C]">{error}</span>}
    </div>
  );
}

function FeedbackRow({ record, adminKey, onReviewed }: { record: FeedbackRecord; adminKey: string; onReviewed: () => void }) {
  const highValue = record.user_verdict === "wrong" && HIGH_VALUE.has(record.model_verdict);
  const modelSaid = VERDICT_LABELS[record.model_verdict] ?? record.model_verdict;
  return (
    <li className="border border-border p-3">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 font-sans text-xs">
        <span className="text-muted">#{record.feedback_id}</span>
        <span className="text-foreground">
          Model: {modelSaid}
          {record.downgraded_from && ` (downgraded from ${VERDICT_LABELS[record.downgraded_from] ?? record.downgraded_from})`}
        </span>
        <span className={record.user_verdict === "wrong" ? "text-[#9B2C2C]" : "text-[#2D6A4F]"}>Reader: {record.user_verdict}</span>
        {highValue && <span className="border border-[#9B2C2C]/40 text-[#9B2C2C] px-1 rounded-sm">high value</span>}
        <span className="text-muted">{record.verified ? "sealed live run" : `unverified ${record.origin} memo`}</span>
        <span className="text-muted">{new Date(record.created_at).toLocaleString()}</span>
        <span className="text-muted ml-auto">
          {record.exported_at ? "exported" : record.status}
          {record.gold_label && ` · gold: ${record.gold_label}`}
        </span>
      </div>
      <p className="font-sans text-sm text-foreground mt-2">&ldquo;{record.claim}&rdquo;</p>
      {record.pitch_excerpt && record.pitch_excerpt !== record.claim && (
        <p className="font-sans text-xs text-muted mt-1">Pitch: {record.pitch_excerpt}</p>
      )}
      {record.evidence_quote ? (
        <p className="font-sans text-xs text-muted mt-1">
          Evidence: &ldquo;{record.evidence_quote}&rdquo;
          {record.evidence_url && (
            <a href={record.evidence_url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-0.5 ml-1 hover:text-foreground">
              source <ExternalLink size={10} />
            </a>
          )}
        </p>
      ) : (
        <p className="font-sans text-xs text-muted mt-1">Evidence: none cited</p>
      )}
      {record.reviewer_note && <p className="font-sans text-xs text-muted mt-1">Note: {record.reviewer_note}</p>}
      {record.status === "pending" && <ReviewControls record={record} adminKey={adminKey} onReviewed={onReviewed} />}
    </li>
  );
}

export default function FeedbackQueue({ adminKey }: { adminKey: string }) {
  const [view, setView] = useState<"disagreements" | "all">("disagreements");
  const [reloads, setReloads] = useState(0);
  const [loaded, setLoaded] = useState<Loaded | null>(null);

  useEffect(() => {
    let active = true;
    fetchFeedback(adminKey, view).then((result) => {
      if (active) setLoaded(result);
    });
    return () => {
      active = false;
    };
  }, [adminKey, view, reloads]);

  const reload = () => setReloads((n) => n + 1);
  const counts = loaded?.ok ? loaded.data.counts : null;

  return (
    <section className="mt-12">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-2">
        <h2 className="font-sans text-xs uppercase tracking-widest text-muted">Verdict feedback</h2>
        <div className="flex border border-border font-sans text-xs">
          {(["disagreements", "all"] as const).map((option) => (
            <button
              key={option}
              type="button"
              onClick={() => setView(option)}
              className={`px-2 py-1 ${view === option ? "bg-foreground text-background" : "text-muted hover:text-foreground"}`}
            >
              {option === "disagreements" ? "Disagreements" : "All"}
            </button>
          ))}
        </div>
      </div>
      <p className="font-sans text-xs text-muted mb-4">
        Readers mark claim verdicts correct or wrong. Accept a row with the correct label, then run{" "}
        <code className="text-foreground">{EXPORT_COMMAND}</code> in <code className="text-foreground">backend/</code> to append it to{" "}
        <code className="text-foreground">evals/candidates.jsonl</code>. Promotion into the golden set is manual.
        {counts &&
          ` ${counts.total} total · ${counts.disagreements} disagreements · ${counts.pending} pending · ${counts.accepted} accepted · ${counts.rejected} rejected · ${counts.exported} exported.`}
      </p>

      {loaded && !loaded.ok && <p className="font-sans text-sm text-[#9B2C2C]">{loaded.message}</p>}
      {loaded?.ok && loaded.data.records.length === 0 && (
        <p className="font-sans text-sm text-muted">
          {view === "disagreements" ? "No disagreements yet." : "No feedback yet."} Every claim verdict in a memo has a correct / wrong control.
        </p>
      )}
      {loaded?.ok && loaded.data.records.length > 0 && (
        <ul className="space-y-2">
          {loaded.data.records.map((record) => (
            <FeedbackRow key={record.feedback_id} record={record} adminKey={adminKey} onReviewed={reload} />
          ))}
        </ul>
      )}
    </section>
  );
}
