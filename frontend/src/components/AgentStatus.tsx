"use client";

type Status =
  | { phase: "planner" }
  | { phase: "scout"; evidenceCount: number }
  | { phase: "critic"; iteration: number; coverageScore: number; feedback: string }
  | { phase: "writer" }
  | { phase: "audit" }
  | { phase: "done" }
  | { phase: "error"; message: string };

interface Props {
  status: Status;
}

const steps = [
  { key: "planner", label: "Research" },
  { key: "scout", label: "Search" },
  { key: "critic", label: "Validate" },
  { key: "writer", label: "Write" },
  { key: "audit", label: "Verify" },
] as const;

const phaseOrder: Record<string, number> = {
  planner: 0,
  scout: 1,
  critic: 2,
  writer: 3,
  audit: 4,
  done: 5,
};

function statusDetail(status: Status): string | null {
  if (status.phase === "planner") return "Generating research queries...";
  if (status.phase === "scout") {
    return status.evidenceCount > 0
      ? `Searching the web · ${status.evidenceCount} sources found`
      : "Searching the web...";
  }
  if (status.phase === "critic") {
    return `Evaluating evidence · Iteration ${status.iteration} · ${Math.round(status.coverageScore * 100)}% coverage`;
  }
  if (status.phase === "writer") return "Synthesizing memo...";
  if (status.phase === "audit") return "Checking every claim against its cited source...";
  return null;
}

export default function AgentStatus({ status }: Props) {
  if (status.phase === "done") return null;

  if (status.phase === "error") {
    return (
      <p className="text-sm font-sans text-muted mb-8">
        Error: {status.message}
      </p>
    );
  }

  const currentIndex = phaseOrder[status.phase] ?? 0;
  const detail = statusDetail(status);

  return (
    <div className="mb-10 font-sans">
      <div className="flex items-center gap-1 mb-3">
        {steps.map((step, i) => (
          <div key={step.key} className="flex items-center flex-1">
            <div
              className={`h-1.5 w-full ${
                i < currentIndex
                  ? "bg-foreground"
                  : i === currentIndex
                    ? "bg-foreground/50"
                    : "bg-border"
              }`}
            />
          </div>
        ))}
      </div>

      <div className="flex gap-1 mb-4">
        {steps.map((step, i) => (
          <span
            key={step.key}
            className={`flex-1 text-xs ${
              i <= currentIndex ? "text-foreground" : "text-muted/50"
            }`}
          >
            {step.label}
          </span>
        ))}
      </div>

      {detail && (
        <p className="text-xs text-muted">{detail}</p>
      )}

      {status.phase === "critic" && status.feedback && (
        <p className="text-xs text-muted mt-1">{status.feedback}</p>
      )}
    </div>
  );
}

export type { Status };
