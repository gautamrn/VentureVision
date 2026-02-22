"use client";

type Status =
  | { phase: "planner" }
  | { phase: "scout"; evidenceCount: number }
  | { phase: "critic"; iteration: number; coverageScore: number; feedback: string }
  | { phase: "writer" }
  | { phase: "done" }
  | { phase: "error"; message: string };

interface Props {
  status: Status;
}

const phaseLabel: Record<string, string> = {
  planner: "Planner · Generating research queries",
  scout: "Scout · Searching the web",
  critic: "Critic · Evaluating evidence",
  writer: "Writer · Synthesizing memo",
};

export default function AgentStatus({ status }: Props) {
  if (status.phase === "done") return null;

  if (status.phase === "error") {
    return (
      <p className="text-sm font-sans text-muted mb-8">
        Error: {status.message}
      </p>
    );
  }

  return (
    <div className="mb-10 font-sans">
      <p className="text-xs text-muted tracking-wide">
        ● {phaseLabel[status.phase] ?? status.phase}
        {status.phase === "scout" && status.evidenceCount > 0 && (
          <span className="ml-2">· {status.evidenceCount} sources found</span>
        )}
        {status.phase === "critic" && (
          <span className="ml-2">
            · Iteration {status.iteration} · Coverage{" "}
            {Math.round(status.coverageScore * 100)}%
          </span>
        )}
      </p>
      {status.phase === "critic" && status.feedback && (
        <p className="text-xs text-muted mt-1 ml-3">{status.feedback}</p>
      )}
    </div>
  );
}

export type { Status };
