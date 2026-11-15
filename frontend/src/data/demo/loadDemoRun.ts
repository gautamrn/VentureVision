import { toAgentEvent } from "@/lib/api";
import { DemoRunSchema, type AgentEvent, type DemoRun, type MemoOutput } from "@/lib/types";
import flakeguard from "./flakeguard.json";
import pantry from "./pantry.json";
import thermalith from "./thermalith.json";
import { DEMO_SAMPLES } from "./samples";

const FIXTURES: Record<string, unknown> = { flakeguard, pantry, thermalith };

export interface ReplayEvent {
  atMs: number;
  event: AgentEvent;
}

export interface ParsedDemoRun extends Omit<DemoRun, "events"> {
  events: ReplayEvent[];
  memo: MemoOutput;
}

export function loadDemoRun(id: string): ParsedDemoRun | null {
  const raw = FIXTURES[id];
  if (!raw) return null;

  const run = DemoRunSchema.parse(raw);
  const events = run.events.map(({ event, atMs, data }) => {
    const parsed = toAgentEvent(event, data);
    if (!parsed) throw new Error(`Demo fixture ${id}: event "${event}" at ${atMs}ms does not match its schema`);
    return { atMs, event: parsed };
  });

  const last = events.at(-1)?.event;
  if (last?.type !== "citation_audit") throw new Error(`Demo fixture ${id}: run does not end with an audited memo`);

  return { ...run, events, memo: last.data.memo };
}

for (const sample of DEMO_SAMPLES) {
  if (!FIXTURES[sample.id]) throw new Error(`Demo sample ${sample.id} has no recorded fixture`);
}
