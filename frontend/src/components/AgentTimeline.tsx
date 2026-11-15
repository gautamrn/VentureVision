"use client";

import { useEffect, useState } from "react";
import { Circle, CircleCheck, CircleDot, CircleSlash, CircleX, RotateCcw, Square } from "lucide-react";
import { STAGES, type CriticCheck, type ScoutRound, type StageKey, type StageStatus, type TimelineState } from "@/lib/timeline";
import { NODE_LABELS, formatDuration } from "@/lib/formatRun";

function hostOf(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

const COVERAGE_TARGET = 0.8;
const MAX_FOLLOW_UP_QUERIES = 4;

const ERROR_KIND_LABELS: Record<string, string> = {
  upstream_api: "External API failure",
  bad_model_output: "Malformed model output",
  internal: "Internal error",
  http: "Request refused",
  network: "Server unreachable",
};

interface Props {
  timeline: TimelineState;
  onCancel?: () => void;
  onRetry?: () => void;
  onStartOver?: () => void;
}

function useNow(ticking: boolean): number {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (!ticking) return;
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, [ticking]);
  return now;
}

function StageIcon({ status }: { status: StageStatus }) {
  const props = { size: 14, className: "shrink-0 mt-px" };
  if (status === "active") return <CircleDot {...props} className={`${props.className} text-foreground`} />;
  if (status === "done") return <CircleCheck {...props} className={`${props.className} text-[#2D6A4F]`} />;
  if (status === "failed") return <CircleX {...props} className={`${props.className} text-[#9B2C2C]`} />;
  if (status === "cancelled") return <CircleSlash {...props} className={`${props.className} text-[#B08B2D]`} />;
  return <Circle {...props} className={`${props.className} text-muted/50`} />;
}

function plannedQueries(timeline: TimelineState, round: number): string[] {
  if (round === 1) return timeline.queries;
  const feedback = timeline.checks.find((c) => c.iteration === round - 1)?.feedback ?? "";
  const queries = feedback.split(",").map((q) => q.trim()).filter(Boolean);
  return (queries.length ? queries : feedback.trim() ? [feedback.trim()] : []).slice(0, MAX_FOLLOW_UP_QUERIES);
}

function sourceCount(timeline: TimelineState): number {
  const reported = [...timeline.rounds].reverse().find((r) => r.evidenceTotal !== null)?.evidenceTotal;
  const streamed = timeline.rounds.reduce((n, r) => n + r.searches.reduce((m, s) => m + s.items.length, 0), 0);
  return Math.max(reported ?? 0, streamed);
}

function stageSummary(stage: StageKey, timeline: TimelineState): string {
  const status = timeline.stages[stage];
  if (status === "pending") return "Waiting";
  const searches = timeline.rounds.flatMap((r) => r.searches);
  const failed = searches.filter((s) => s.status === "error").length;

  if (stage === "planner") {
    return status === "active" ? "Turning the pitch into web search queries" : `${timeline.queries.length} search queries`;
  }
  if (stage === "scout") {
    const round = timeline.rounds.at(-1);
    if (status === "active" && round) {
      const planned = plannedQueries(timeline, round.round).length;
      return `Round ${round.round} · ${round.searches.length} of ${planned || "?"} searches back · ${sourceCount(timeline)} sources so far`;
    }
    const failedNote = failed > 0 ? ` · ${failed} failed` : "";
    return `${sourceCount(timeline)} sources from ${searches.length} searches in ${timeline.rounds.length} round${timeline.rounds.length === 1 ? "" : "s"}${failedNote}`;
  }
  if (stage === "critic") {
    const scores = timeline.checks.filter((c) => c.coverageScore !== null).map((c) => `${Math.round((c.coverageScore ?? 0) * 100)}%`);
    if (status === "active") return `Judging coverage of the research plan · round ${timeline.checks.length + 1}`;
    return scores.length ? `Coverage ${scores.join(" → ")} (target ${COVERAGE_TARGET * 100}%)` : "Checked coverage";
  }
  if (status === "active") {
    return timeline.auditing
      ? "Checking every cited quote against its source"
      : `Writing the memo from ${sourceCount(timeline)} sources`;
  }
  return status === "done" ? "Memo written and citations verified" : NODE_LABELS.writer;
}

function SearchList({ round, timeline }: { round: ScoutRound; timeline: TimelineState }) {
  const returned = new Set(round.searches.map((s) => s.query));
  const scoutStatus = timeline.stages.scout;
  const unreturnedLabel =
    scoutStatus === "active" ? "waiting for Tavily"
    : scoutStatus === "cancelled" ? "not run (cancelled)"
    : scoutStatus === "failed" ? "not run (scout failed)"
    : null;
  const unreturned = unreturnedLabel && round === timeline.rounds.at(-1)
    ? plannedQueries(timeline, round.round).filter((q) => !returned.has(q))
    : [];

  return (
    <div className="mt-2">
      <p className="text-[11px] uppercase tracking-widest text-muted mb-1">Round {round.round}</p>
      <ul className="space-y-1.5">
        {round.searches.map((search, i) => (
          <li key={i}>
            <p className="text-foreground">{search.query}</p>
            {search.status === "error" ? (
              <p className="text-[#9B2C2C]">Search failed ({search.error ?? "unknown error"}) — not counted as evidence</p>
            ) : search.items.length === 0 ? (
              <p className="text-muted">No results for this query</p>
            ) : (
              <ul>
                {search.items.map((item) => (
                  <li key={item.url} className="text-muted truncate">
                    {item.title || "Untitled"} <span className="text-muted/70">— {hostOf(item.url)}</span>
                  </li>
                ))}
              </ul>
            )}
          </li>
        ))}
        {unreturned.map((query) => (
          <li key={query} className="text-muted/70">
            {query} <span>· {unreturnedLabel}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function CheckRow({ check }: { check: CriticCheck }) {
  const score = check.coverageScore;
  let verdict: string;
  if (check.budgetExitReason) verdict = check.budgetExitReason;
  else if (check.capReached) verdict = "Iteration cap reached; writing with the evidence so far";
  else if (check.isValidated) verdict = "Enough evidence; handing off to the writer";
  else verdict = `Not enough yet; asked the scout for ${check.feedback.split(",").filter((q) => q.trim()).length || 1} more searches`;

  return (
    <li className="flex flex-wrap items-start gap-x-3 gap-y-0.5">
      <span className="text-muted w-16 shrink-0">Round {check.iteration}</span>
      {score !== null ? (
        <span className="flex items-center gap-2 shrink-0">
          <span className="relative block w-24 h-1.5 bg-border mt-px">
            <span className="absolute inset-y-0 left-0 bg-foreground" style={{ width: `${Math.round(score * 100)}%` }} />
            <span className="absolute -inset-y-0.5 w-px bg-[#2D6A4F]" style={{ left: `${COVERAGE_TARGET * 100}%` }} />
          </span>
          <span className="w-9 text-foreground">{Math.round(score * 100)}%</span>
        </span>
      ) : (
        <span className="w-[8.5rem] shrink-0 text-muted">no new score</span>
      )}
      <span className={`min-w-[12rem] flex-1 ${check.budgetExitReason ? "text-[#B08B2D]" : "text-muted"}`}>{verdict}</span>
    </li>
  );
}

function OutcomePanel({ timeline, onCancel, onRetry, onStartOver }: Props) {
  const { outcome } = timeline;
  const button = "inline-flex items-center gap-1.5 border border-border px-3 py-1.5 rounded-sm text-xs text-foreground hover:border-foreground";

  if (outcome.kind === "running") {
    return onCancel ? (
      <button onClick={onCancel} className={button}>
        <Square size={11} /> Cancel run
      </button>
    ) : null;
  }
  if (outcome.kind === "cancelling") {
    return (
      <p className="text-muted">
        Cancelling. The server stops before the next step; an API call already in flight finishes first.
      </p>
    );
  }
  if (outcome.kind === "cancelled") {
    const where = outcome.stage ? ` during the ${NODE_LABELS[outcome.stage].toLowerCase()} step` : "";
    return (
      <div className="flex flex-wrap items-center gap-3">
        <p className="text-[#B08B2D]">
          {outcome.confirmed
            ? `Run cancelled${where}. The server confirmed it stopped; no further agents ran.`
            : `Run cancelled${where}. The connection closed before the server confirmed the stop.`}
        </p>
        {onStartOver && <button onClick={onStartOver} className={button}>Start a new analysis</button>}
      </div>
    );
  }
  if (outcome.kind === "disconnected") {
    return (
      <div className="flex flex-wrap items-center gap-3">
        <p className="text-[#9B2C2C]">
          The connection to the server closed before the run finished. The server stops runs whose client disconnects.
        </p>
        {onStartOver && <button onClick={onStartOver} className={button}>Start a new analysis</button>}
      </div>
    );
  }
  if (outcome.kind === "failed") {
    return (
      <div className="space-y-2">
        <p>
          <span className="uppercase tracking-widest text-[#9B2C2C]">{ERROR_KIND_LABELS[outcome.errorKind] ?? "Error"}</span>
          {outcome.stage && <span className="text-muted"> · {NODE_LABELS[outcome.stage]}</span>}
        </p>
        <p className="text-foreground">{outcome.message}</p>
        <p className="text-muted">
          {outcome.stage
            ? "This is a failure, not an empty result: the run stopped instead of writing a memo from missing data."
            : "No agents ran, so there is no partial result."}
        </p>
        <div className="flex flex-wrap items-center gap-3">
          {outcome.retryable && onRetry && outcome.stage && (
            <button onClick={onRetry} className={button}>
              <RotateCcw size={11} /> Retry from {NODE_LABELS[outcome.stage]}
              {timeline.retriesLeft !== null && <span className="text-muted">({timeline.retriesLeft} left)</span>}
            </button>
          )}
          {onStartOver && <button onClick={onStartOver} className={button}>Start a new analysis</button>}
        </div>
      </div>
    );
  }
  return null;
}

export default function AgentTimeline(props: Props) {
  const { timeline } = props;
  const ticking = STAGES.some((s) => timeline.stages[s] === "active");
  const now = useNow(ticking);

  if (timeline.outcome.kind === "done") return null;

  return (
    <section className="mb-10 font-sans text-xs" aria-label="Agent timeline">
      <ol className="border-t border-border">
        {STAGES.map((stage) => {
          const status = timeline.stages[stage];
          const since = timeline.activeSince[stage];
          const ms = timeline.stageMs[stage] + (status === "active" && since !== null ? Math.max(0, now - since) : 0);
          return (
            <li key={stage} className="border-b border-border py-3">
              <div className="flex items-start gap-2">
                <StageIcon status={status} />
                <span className={`w-[4.5rem] shrink-0 uppercase tracking-widest ${status === "pending" ? "text-muted/50" : "text-foreground"}`}>
                  {NODE_LABELS[stage]}
                </span>
                <span className={`flex-1 ${status === "pending" ? "text-muted/50" : "text-muted"}`}>{stageSummary(stage, timeline)}</span>
                {status !== "pending" && ms > 0 && <span className="text-muted tabular-nums">{formatDuration(ms)}</span>}
              </div>

              <div className="pl-[6.375rem]">
                {stage === "planner" && timeline.queries.length > 0 && (
                  <ul className="mt-2 space-y-0.5 text-muted">
                    {timeline.queries.map((q) => (
                      <li key={q}>{q}</li>
                    ))}
                  </ul>
                )}
                {stage === "scout" && timeline.rounds.filter((r) => r.searches.length > 0 || status === "active").map((round) => (
                  <SearchList key={round.round} round={round} timeline={timeline} />
                ))}
                {stage === "critic" && timeline.checks.length > 0 && (
                  <ul className="mt-2 space-y-1.5">
                    {timeline.checks.map((check, i) => (
                      <CheckRow key={i} check={check} />
                    ))}
                  </ul>
                )}
              </div>
            </li>
          );
        })}
      </ol>
      <div className="mt-4">
        <OutcomePanel {...props} />
      </div>
    </section>
  );
}
