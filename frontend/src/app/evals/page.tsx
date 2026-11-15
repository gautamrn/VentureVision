import type { Metadata } from "next";
import Link from "next/link";
import summaryJson from "@/data/evals/summary.json";
import { formatRunDate, formatUsd } from "@/lib/formatRun";
import {
  EvalSummarySchema,
  type EvalLabel,
  type EvalRunSummary,
  type FailedCase,
  type LatestEvalRun,
} from "@/lib/types";

export const metadata: Metadata = {
  title: "Evals · VentureVision",
  description: "How often VentureVision's claim verdicts match hand-labeled answers.",
};

const LABELS: EvalLabel[] = ["supported", "unsupported", "contradicted"];

const LABEL_COLOR: Record<EvalLabel, string> = {
  supported: "text-[#2D6A4F]",
  unsupported: "text-[#B08B2D]",
  contradicted: "text-[#9B2C2C]",
};

const MODE_NAME = {
  heuristic: "Heuristic baseline",
  llm: "LLM verifier",
} as const;

function modeDescription(run: Pick<EvalRunSummary, "mode" | "model">): string {
  return run.mode === "heuristic"
    ? "No model: word overlap, number and direction checks"
    : `${run.model ?? "model"} with the pipeline's verdict and quote rules`;
}

function labelAccuracy(run: EvalRunSummary, label: EvalLabel): string {
  const score = run.labels.find((s) => s.label === label);
  return score && score.total > 0 ? `${score.accuracy}% (${score.correct}/${score.total})` : "—";
}

function correctCount(run: EvalRunSummary): number {
  return run.labels.reduce((sum, s) => sum + s.correct, 0);
}

function ScoreRow({ mode, run, command }: { mode: keyof typeof MODE_NAME; run: LatestEvalRun | null; command: string }) {
  const cell = "py-2.5 pr-4 align-top";
  if (!run) {
    return (
      <tr className="border-b border-border">
        <td className={cell}>
          <p className="text-foreground">{MODE_NAME[mode]}</p>
        </td>
        <td className={`${cell} text-muted`} colSpan={5}>
          Not run yet. <code className="text-[11px] text-foreground">{command}</code>
        </td>
      </tr>
    );
  }
  return (
    <tr className="border-b border-border">
      <td className={cell}>
        <p className="text-foreground">{MODE_NAME[mode]}</p>
        <p className="text-muted mt-0.5">{modeDescription(run)}</p>
      </td>
      <td className={`${cell} font-serif text-lg text-foreground`}>
        {run.overall_accuracy}%
        <span className="font-sans text-xs text-muted"> ({correctCount(run)}/{run.case_count})</span>
      </td>
      {LABELS.map((label) => (
        <td key={label} className={`${cell} text-foreground whitespace-nowrap`}>
          {labelAccuracy(run, label)}
        </td>
      ))}
      <td className={`${cell} text-muted whitespace-nowrap`}>
        {formatRunDate(run.started_at)}
        <br />
        {run.mode === "llm" ? formatUsd(run.cost_usd) : "$0"}
      </td>
    </tr>
  );
}

function FailureItem({ failure }: { failure: FailedCase }) {
  return (
    <details className="border border-border rounded-sm">
      <summary className="cursor-pointer px-3 py-2 flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <span className="text-muted w-14 shrink-0">{failure.id}</span>
        <span className="text-foreground flex-1 min-w-[200px]">{failure.claim}</span>
        <span className="whitespace-nowrap">
          <span className={LABEL_COLOR[failure.expected]}>{failure.expected}</span>
          <span className="text-muted"> expected · got </span>
          <span className={LABEL_COLOR[failure.predicted]}>{failure.predicted}</span>
        </span>
      </summary>
      <dl className="px-3 pb-3 pt-1 grid grid-cols-[110px_1fr] gap-x-3 gap-y-2 border-t border-border">
        <dt className="text-muted">Pitch</dt>
        <dd className="text-foreground">{failure.pitch_excerpt || "—"}</dd>
        <dt className="text-muted">Evidence</dt>
        <dd className="text-foreground space-y-1.5">
          {failure.evidence.length === 0
            ? "None. No evidence item addresses the claim."
            : failure.evidence.map((item, i) => (
                <p key={i}>
                  &ldquo;{item.text}&rdquo;
                  {item.source_url && (
                    <>
                      {" "}
                      <a href={item.source_url} target="_blank" rel="noreferrer" className="text-muted underline">
                        {new URL(item.source_url).hostname}
                      </a>
                    </>
                  )}
                </p>
              ))}
        </dd>
        <dt className="text-muted">Verifier said</dt>
        <dd className="text-foreground">
          {failure.detail}
          {failure.downgraded_from && (
            <span className="text-muted"> (answered {failure.downgraded_from}; downgraded, quote not found in evidence)</span>
          )}
        </dd>
        <dt className="text-muted">Why the label</dt>
        <dd className="text-foreground">{failure.notes}</dd>
        <dt className="text-muted">Case origin</dt>
        <dd className="text-muted">{failure.origin}</dd>
      </dl>
    </details>
  );
}

function FailureBrowser({ run }: { run: LatestEvalRun }) {
  return (
    <section className="mb-12">
      <h2 className="text-xs uppercase tracking-widest text-foreground mb-1">
        {MODE_NAME[run.mode]} misses ({run.failures.length})
      </h2>
      <p className="text-muted mb-3">Latest run, {formatRunDate(run.started_at)}. Click a case for the evidence.</p>
      {run.failures.length === 0 ? (
        <p className="text-muted">No misses in this run.</p>
      ) : (
        <div className="space-y-1.5">
          {run.failures.map((failure) => (
            <FailureItem key={failure.id} failure={failure} />
          ))}
        </div>
      )}
    </section>
  );
}

export default function EvalsPage() {
  const summary = EvalSummarySchema.parse(summaryJson);
  const { dataset } = summary;
  const history = [...summary.history].reverse();

  return (
    <main className="min-h-screen bg-background px-6 py-16">
      <div className="w-full max-w-4xl mx-auto font-sans text-xs">
        <Link href="/" className="text-muted tracking-widest uppercase mb-8 block">
          &larr; VentureVision
        </Link>
        <h1 className="font-serif text-3xl text-foreground mb-1">Evals</h1>
        <p className="text-sm text-muted mb-8 max-w-2xl">
          How often a claim verdict matches a hand-assigned label, given fixed evidence. This scores the verdict step only;
          it does not score web retrieval or the memo&apos;s other sections.
        </p>

        <section className="border border-border rounded-sm p-4 mb-10 grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <p className="uppercase tracking-widest text-muted mb-1">Dataset</p>
            <p className="text-foreground text-sm">
              {dataset.name} v{dataset.version}
            </p>
            <p className="text-muted">updated {dataset.updated}</p>
          </div>
          <div>
            <p className="uppercase tracking-widest text-muted mb-1">Cases</p>
            <p className="font-serif text-2xl text-foreground">{dataset.case_count}</p>
          </div>
          <div>
            <p className="uppercase tracking-widest text-muted mb-1">Labels</p>
            {LABELS.map((label) => (
              <p key={label}>
                <span className={LABEL_COLOR[label]}>{label}</span>{" "}
                <span className="text-foreground">{dataset.label_counts[label] ?? 0}</span>
              </p>
            ))}
          </div>
          <div>
            <p className="uppercase tracking-widest text-muted mb-1">Origin</p>
            {Object.entries(dataset.origin_counts).map(([origin, count]) => (
              <p key={origin} className="text-foreground">
                {origin} <span className="text-muted">{count}</span>
              </p>
            ))}
            <p className="text-muted mt-1">{dataset.candidate_count} user-feedback candidates awaiting review</p>
          </div>
        </section>

        <section className="mb-12">
          <h2 className="uppercase tracking-widest text-foreground mb-3">Latest scores</h2>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[720px]">
              <thead>
                <tr className="border-b border-border text-left text-muted">
                  <th className="pb-2 pr-4 font-normal">Verifier</th>
                  <th className="pb-2 pr-4 font-normal">Overall</th>
                  {LABELS.map((label) => (
                    <th key={label} className={`pb-2 pr-4 font-normal ${LABEL_COLOR[label]}`}>
                      {label}
                    </th>
                  ))}
                  <th className="pb-2 pr-4 font-normal">Run · cost</th>
                </tr>
              </thead>
              <tbody>
                <ScoreRow mode="heuristic" run={summary.latest_heuristic} command="python evals/run_evals.py --mode heuristic --publish" />
                <ScoreRow mode="llm" run={summary.latest_llm} command="python evals/run_evals.py --mode llm --publish" />
              </tbody>
            </table>
          </div>
          {summary.baseline && (
            <p className="text-muted mt-3">
              CI fails a pull request if heuristic accuracy drops more than 3 points below the stored baseline (
              {summary.baseline.overall_accuracy}% on v{summary.baseline.dataset_version}).
            </p>
          )}
        </section>

        <section className="mb-12">
          <h2 className="uppercase tracking-widest text-foreground mb-3">Run history</h2>
          <table className="w-full">
            <thead>
              <tr className="border-b border-border text-left text-muted">
                <th className="pb-2 pr-4 font-normal">Run</th>
                <th className="pb-2 pr-4 font-normal">Verifier</th>
                <th className="pb-2 pr-4 font-normal">Dataset</th>
                <th className="pb-2 pr-4 font-normal w-1/3">Overall</th>
              </tr>
            </thead>
            <tbody>
              {history.map((run) => (
                <tr key={run.run_id} className="border-b border-border">
                  <td className="py-2 pr-4 text-muted whitespace-nowrap">{formatRunDate(run.started_at)}</td>
                  <td className="py-2 pr-4 text-foreground">{MODE_NAME[run.mode]}</td>
                  <td className="py-2 pr-4 text-muted">
                    v{run.dataset_version} · {run.case_count} cases
                  </td>
                  <td className="py-2 pr-4">
                    <div className="flex items-center gap-2">
                      <div className="flex-1 h-2 bg-border" aria-hidden>
                        <div className="h-full bg-foreground" style={{ width: `${run.overall_accuracy}%` }} />
                      </div>
                      <span className="text-foreground w-12 text-right">{run.overall_accuracy}%</span>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>

        {summary.latest_llm && <FailureBrowser run={summary.latest_llm} />}
        {summary.latest_heuristic && <FailureBrowser run={summary.latest_heuristic} />}

        <section className="border-t border-border pt-6 text-muted max-w-2xl space-y-2">
          <p>
            The dataset comes from the three demo runs: every evidence quote is verbatim from a source the Scout retrieved.
            Some claims are copied from the demo pitches; others were written to test one verdict boundary against a real
            quote. All labels were assigned by hand, by the same person who wrote the heuristic, so treat the heuristic
            score as a floor rather than a fair competitor.
          </p>
          <p>Data generated {formatRunDate(summary.generated_at)} by evals/run_evals.py.</p>
        </section>
      </div>
    </main>
  );
}
