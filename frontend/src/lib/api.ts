import {
  AgentEvent,
  PlannerEventSchema,
  ScoutEventSchema,
  CriticEventSchema,
  WriterEventSchema,
  CitationAuditEventSchema,
} from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:3001";

function parseEvent(eventName: string, rawData: string): AgentEvent | null {
  try {
    const data = JSON.parse(rawData);

    if (eventName === "planner") {
      return { type: "planner", data: PlannerEventSchema.parse(data) };
    }
    if (eventName === "scout") {
      return { type: "scout", data: ScoutEventSchema.parse(data) };
    }
    if (eventName === "critic") {
      return { type: "critic", data: CriticEventSchema.parse(data) };
    }
    if (eventName === "writer") {
      return { type: "writer", data: WriterEventSchema.parse(data) };
    }
    if (eventName === "citation_audit") {
      return { type: "citation_audit", data: CitationAuditEventSchema.parse(data) };
    }
    if (eventName === "error") {
      return { type: "error", data };
    }
  } catch {
    return null;
  }
  return null;
}

export async function streamAnalysis(
  pitch: string,
  mode: string,
  onEvent: (event: AgentEvent) => void,
  onDone: () => void
): Promise<void> {
  const response = await fetch(`${API_URL}/analyze/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ pitch, mode }),
  });

  if (!response.ok || !response.body) {
    if (response.status === 429) {
      const body = await response.json().catch(() => null);
      const detail = body?.detail ?? "Rate limit exceeded. Please try again later.";
      onEvent({ type: "error", data: { message: detail } });
    } else if (response.status === 503) {
      onEvent({ type: "error", data: { message: "Server is busy. Please try again in a minute." } });
    } else if (response.status === 422) {
      onEvent({ type: "error", data: { message: "Pitch must be between 40 and 5,000 characters." } });
    } else {
      onEvent({ type: "error", data: { message: "Failed to connect to analysis server." } });
    }
    onDone();
    return;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let currentEvent = "";

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
        const rawData = line.slice(6).trim();
        if (currentEvent) {
          const parsed = parseEvent(currentEvent, rawData);
          if (parsed) onEvent(parsed);
          currentEvent = "";
        }
      }
    }
  }

  onDone();
}
