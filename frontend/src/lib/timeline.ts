import type { AgentEvent, EvidenceEvent, MemoOutput } from "./types";

export const STAGES = ["planner", "scout", "critic", "writer"] as const;
export type StageKey = (typeof STAGES)[number];
export type StageStatus = "pending" | "active" | "done" | "failed" | "cancelled";

export type SearchRow = Pick<EvidenceEvent, "query" | "status" | "error" | "items">;

export interface ScoutRound {
  round: number;
  searches: SearchRow[];
  evidenceTotal: number | null;
}

export interface CriticCheck {
  iteration: number;
  coverageScore: number | null;
  isValidated: boolean;
  feedback: string;
  capReached: boolean;
  budgetExitReason: string | null;
}

export type ErrorKind = "upstream_api" | "bad_model_output" | "internal" | "http" | "network";

export type Outcome =
  | { kind: "running" }
  | { kind: "cancelling" }
  | { kind: "done" }
  | { kind: "cancelled"; stage: StageKey | null; confirmed: boolean }
  | { kind: "failed"; stage: StageKey | null; message: string; errorKind: ErrorKind; retryable: boolean }
  | { kind: "disconnected" };

export interface TimelineState {
  runId: string | null;
  attempt: number;
  retriesLeft: number | null;
  budgetUsd: number | null;
  stages: Record<StageKey, StageStatus>;
  activeSince: Record<StageKey, number | null>;
  stageMs: Record<StageKey, number>;
  queries: string[];
  rounds: ScoutRound[];
  checks: CriticCheck[];
  auditing: boolean;
  memo: MemoOutput | null;
  outcome: Outcome;
}

export type TimelineAction =
  | { type: "started"; at: number }
  | { type: "event"; event: AgentEvent; at: number }
  | { type: "cancelRequested" }
  | { type: "streamEnded" }
  | { type: "retryStarted"; at: number };

const byStage = <T>(value: T): Record<StageKey, T> => ({ planner: value, scout: value, critic: value, writer: value });

export function initialTimeline(): TimelineState {
  return {
    runId: null,
    attempt: 1,
    retriesLeft: null,
    budgetUsd: null,
    stages: { ...byStage<StageStatus>("pending"), planner: "active" },
    activeSince: byStage<number | null>(null),
    stageMs: byStage(0),
    queries: [],
    rounds: [],
    checks: [],
    auditing: false,
    memo: null,
    outcome: { kind: "running" },
  };
}

function toStage(node: string | null | undefined): StageKey | null {
  if (node === "citation_audit") return "writer";
  return (STAGES as readonly string[]).includes(node ?? "") ? (node as StageKey) : null;
}

function activeStage(state: TimelineState): StageKey | null {
  return STAGES.find((s) => state.stages[s] === "active") ?? null;
}

function setStage(state: TimelineState, stage: StageKey, status: StageStatus, at: number): TimelineState {
  const since = state.activeSince[stage];
  const wasActive = state.stages[stage] === "active" && since !== null;
  return {
    ...state,
    stages: { ...state.stages, [stage]: status },
    activeSince: { ...state.activeSince, [stage]: status === "active" ? (wasActive ? since : at) : null },
    stageMs: wasActive && status !== "active" ? { ...state.stageMs, [stage]: state.stageMs[stage] + (at - since) } : state.stageMs,
  };
}

function withRound(state: TimelineState, round: number): TimelineState {
  if (state.rounds.some((r) => r.round === round)) return state;
  return { ...state, rounds: [...state.rounds, { round, searches: [], evidenceTotal: null }] };
}

function applyEvent(state: TimelineState, event: AgentEvent, at: number): TimelineState {
  switch (event.type) {
    case "run":
      return {
        ...state,
        runId: event.data.runId,
        attempt: event.data.attempt,
        retriesLeft: event.data.retriesLeft,
        budgetUsd: event.data.budgetUsd,
      };
    case "planner": {
      const next = setStage(setStage({ ...state, queries: event.data.queries }, "planner", "done", at), "scout", "active", at);
      return withRound(next, 1);
    }
    case "evidence": {
      let next = withRound(state, event.data.round);
      if (next.stages.scout !== "active") next = setStage(next, "scout", "active", at);
      const { query, status, error, items } = event.data;
      return {
        ...next,
        rounds: next.rounds.map((r) =>
          r.round === event.data.round ? { ...r, searches: [...r.searches, { query, status, error, items }] } : r
        ),
      };
    }
    case "scout": {
      const lastRound = state.rounds.at(-1)?.round ?? 1;
      const next = withRound(state, lastRound);
      return setStage(
        setStage(
          {
            ...next,
            rounds: next.rounds.map((r) => (r.round === lastRound ? { ...r, evidenceTotal: event.data.evidenceCount } : r)),
          },
          "scout",
          "done",
          at
        ),
        "critic",
        "active",
        at
      );
    }
    case "critic": {
      const check: CriticCheck = {
        iteration: event.data.iteration,
        coverageScore: event.data.coverageScore,
        isValidated: event.data.isValidated,
        feedback: event.data.feedback,
        capReached: event.data.iterationCapReached ?? false,
        budgetExitReason: event.data.budgetExitReason ?? null,
      };
      const next = setStage({ ...state, checks: [...state.checks, check] }, "critic", "done", at);
      return event.data.isValidated
        ? setStage(next, "writer", "active", at)
        : withRound(setStage(next, "scout", "active", at), event.data.iteration + 1);
    }
    case "writer":
      return event.data.memoReady
        ? { ...state, auditing: true }
        : {
            ...setStage(state, "writer", "failed", at),
            outcome: { kind: "failed", stage: "writer", message: "The writer produced no memo.", errorKind: "internal", retryable: false },
          };
    case "citation_audit":
      return { ...setStage(state, "writer", "done", at), memo: event.data.memo, auditing: false, outcome: { kind: "done" } };
    case "cancelled": {
      const stage = toStage(event.data.node) ?? activeStage(state);
      const next = stage ? setStage(state, stage, "cancelled", at) : state;
      return { ...next, outcome: { kind: "cancelled", stage, confirmed: true } };
    }
    case "error": {
      const kind = event.data.kind ?? "internal";
      const refusedBeforeStart = !event.data.node && state.runId === null && (kind === "http" || kind === "network");
      if (refusedBeforeStart) {
        const active = activeStage(state);
        const next = active ? setStage(state, active, "pending", at) : state;
        return { ...next, outcome: { kind: "failed", stage: null, message: event.data.message, errorKind: kind, retryable: false } };
      }
      const stage = toStage(event.data.node) ?? activeStage(state);
      const next = stage ? setStage(state, stage, "failed", at) : state;
      return {
        ...next,
        runId: event.data.runId ?? next.runId,
        outcome: {
          kind: "failed",
          stage,
          message: event.data.message,
          errorKind: kind,
          retryable: Boolean(event.data.retryable && (event.data.runId ?? next.runId)),
        },
      };
    }
  }
}

export function timelineReducer(state: TimelineState, action: TimelineAction): TimelineState {
  switch (action.type) {
    case "started":
      return { ...state, activeSince: { ...state.activeSince, planner: action.at } };
    case "event":
      return applyEvent(state, action.event, action.at);
    case "cancelRequested":
      return state.outcome.kind === "running" ? { ...state, outcome: { kind: "cancelling" } } : state;
    case "streamEnded":
      if (state.outcome.kind === "running") return { ...state, outcome: { kind: "disconnected" } };
      if (state.outcome.kind === "cancelling") {
        return { ...state, outcome: { kind: "cancelled", stage: activeStage(state), confirmed: false } };
      }
      return state;
    case "retryStarted": {
      if (state.outcome.kind !== "failed" || !state.outcome.stage) return state;
      const stage = state.outcome.stage;
      const rounds =
        stage === "scout" ? state.rounds.map((r, i) => (i === state.rounds.length - 1 ? { ...r, searches: [] } : r)) : state.rounds;
      return { ...setStage({ ...state, rounds }, stage, "active", action.at), outcome: { kind: "running" } };
    }
  }
}

export function isTerminal(outcome: Outcome): boolean {
  return outcome.kind !== "running" && outcome.kind !== "cancelling";
}
