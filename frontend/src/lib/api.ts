import {
  AgentEvent,
  CancelResponseSchema,
  CancelledEventSchema,
  CitationAuditEventSchema,
  CriticEventSchema,
  ErrorEventSchema,
  EvidenceEventSchema,
  PlannerEventSchema,
  RunEventSchema,
  ScoutEventSchema,
  WriterEventSchema,
} from "./types";

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:3001";

const EVENT_SCHEMAS = {
  run: RunEventSchema,
  planner: PlannerEventSchema,
  evidence: EvidenceEventSchema,
  scout: ScoutEventSchema,
  critic: CriticEventSchema,
  writer: WriterEventSchema,
  citation_audit: CitationAuditEventSchema,
  cancelled: CancelledEventSchema,
  error: ErrorEventSchema,
} as const;

export function toAgentEvent(eventName: string, data: unknown): AgentEvent | null {
  if (!(eventName in EVENT_SCHEMAS)) return null;
  const type = eventName as keyof typeof EVENT_SCHEMAS;
  const parsed = EVENT_SCHEMAS[type].safeParse(data);
  return parsed.success ? ({ type, data: parsed.data } as AgentEvent) : null;
}

function parseEvent(eventName: string, rawData: string): AgentEvent | null {
  try {
    return toAgentEvent(eventName, JSON.parse(rawData));
  } catch {
    return null;
  }
}

async function httpErrorEvent(response: Response): Promise<AgentEvent> {
  const body = await response.json().catch(() => null);
  const detail = typeof body?.detail === "string" ? body.detail : null;
  const messages: Record<number, string> = {
    404: detail ?? "This run is no longer on the server.",
    409: detail ?? "This run cannot be retried.",
    422: "Pitch must be between 40 and 5,000 characters.",
    429: detail ?? "Rate limit exceeded. Please try again later.",
    503: "Server is busy. Please try again in a minute.",
  };
  return {
    type: "error",
    data: {
      message: messages[response.status] ?? `The analysis server returned HTTP ${response.status}.`,
      kind: "http",
      retryable: false,
    },
  };
}

function isAbort(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError";
}

async function streamEvents(
  path: string,
  body: unknown,
  onEvent: (event: AgentEvent) => void,
  signal: AbortSignal
): Promise<void> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal,
    });
  } catch (error) {
    if (isAbort(error)) return;
    onEvent({
      type: "error",
      data: { message: `Could not reach the analysis server at ${API_URL}.`, kind: "network", retryable: false },
    });
    return;
  }

  if (!response.ok || !response.body) {
    onEvent(await httpErrorEvent(response));
    return;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let currentEvent = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() ?? "";

      for (const line of lines) {
        if (line.startsWith("event: ")) {
          currentEvent = line.slice(7).trim();
        } else if (line.startsWith("data: ")) {
          if (currentEvent) {
            const parsed = parseEvent(currentEvent, line.slice(6).trim());
            if (parsed) onEvent(parsed);
            currentEvent = "";
          }
        }
      }
    }
  } catch (error) {
    if (!isAbort(error)) throw error;
  }
}

export function startAnalysis(
  pitch: string,
  mode: string,
  onEvent: (event: AgentEvent) => void,
  signal: AbortSignal
): Promise<void> {
  return streamEvents("/analyze/stream", { pitch, mode }, onEvent, signal);
}

export function retryRun(runId: string, onEvent: (event: AgentEvent) => void, signal: AbortSignal): Promise<void> {
  return streamEvents(`/runs/${encodeURIComponent(runId)}/retry`, {}, onEvent, signal);
}

export async function cancelRun(runId: string): Promise<boolean> {
  try {
    const response = await fetch(`${API_URL}/runs/${encodeURIComponent(runId)}/cancel`, { method: "POST" });
    return response.ok && CancelResponseSchema.safeParse(await response.json()).success;
  } catch {
    return false;
  }
}
