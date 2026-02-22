import { z } from "zod";

export const MarketCompetitorSchema = z.object({
  competitor: z.string(),
  pricing: z.string(),
  funding: z.string(),
});

export const MemoOutputSchema = z.object({
  executive_summary: z.string(),
  market_matrix: z.array(MarketCompetitorSchema),
  risk_vectors: z.array(z.string()),
  confidence_score: z.number(),
  citation_links: z.array(z.string()),
});

export const PlannerEventSchema = z.object({
  queries: z.array(z.string()),
  queryCount: z.number(),
});

export const ScoutEventSchema = z.object({
  evidenceCount: z.number(),
});

export const CriticEventSchema = z.object({
  iteration: z.number(),
  isValidated: z.boolean(),
  coverageScore: z.number(),
  feedback: z.string(),
});

export const WriterEventSchema = z.object({
  memo: MemoOutputSchema,
});

export type MarketCompetitor = z.infer<typeof MarketCompetitorSchema>;
export type MemoOutput = z.infer<typeof MemoOutputSchema>;
export type PlannerEvent = z.infer<typeof PlannerEventSchema>;
export type ScoutEvent = z.infer<typeof ScoutEventSchema>;
export type CriticEvent = z.infer<typeof CriticEventSchema>;
export type WriterEvent = z.infer<typeof WriterEventSchema>;

export type AgentEvent =
  | { type: "planner"; data: PlannerEvent }
  | { type: "scout"; data: ScoutEvent }
  | { type: "critic"; data: CriticEvent }
  | { type: "writer"; data: WriterEvent }
  | { type: "error"; data: { message: string } };
