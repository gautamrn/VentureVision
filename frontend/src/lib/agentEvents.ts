import type { Status } from "@/components/AgentStatus";
import type { AgentEvent } from "./types";

export function statusForEvent(event: AgentEvent): Status {
  switch (event.type) {
    case "planner":
      return { phase: "scout", evidenceCount: 0 };
    case "scout":
      return { phase: "scout", evidenceCount: event.data.evidenceCount };
    case "critic":
      return event.data.isValidated
        ? { phase: "writer" }
        : {
            phase: "critic",
            iteration: event.data.iteration,
            coverageScore: event.data.coverageScore,
            feedback: event.data.feedback,
          };
    case "writer":
      return event.data.memoReady
        ? { phase: "audit" }
        : { phase: "error", message: "Analysis failed. Please try again." };
    case "citation_audit":
      return { phase: "done" };
    case "error":
      return { phase: "error", message: event.data.message };
  }
}
