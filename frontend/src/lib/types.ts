import { z } from "zod";

export const MarketCompetitorSchema = z.object({
  competitor: z.string(),
  pricing: z.string(),
  funding: z.string(),
});

export const SubscoresSchema = z.object({
  market_size: z.number(),
  competition: z.number(),
  revenue_model: z.number(),
  uniqueness: z.number(),
});

export const InvestorQuestionSchema = z.object({
  question: z.string(),
  why_it_matters: z.string(),
});

export const PitchAnnotationSchema = z.object({
  excerpt: z.string(),
  annotation_type: z.string(),
  note: z.string(),
});

export const DealContextSchema = z.object({
  typical_stage: z.string(),
  typical_raise_range: z.string(),
  typical_dilution: z.string(),
  red_flags: z.array(z.string()),
});

export const MemoOutputSchema = z.object({
  pitch_score: z.number(),
  subscores: SubscoresSchema,
  strengthen_suggestions: z.array(z.string()),
  executive_summary: z.string(),
  market_matrix: z.array(MarketCompetitorSchema),
  risk_vectors: z.array(z.string()),
  confidence_score: z.number(),
  citation_links: z.array(z.string()),
  investor_questions: z.array(InvestorQuestionSchema),
  pitch_annotations: z.array(PitchAnnotationSchema),
  deal_context: DealContextSchema,
  feature_suggestions: z.array(z.string()),
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
export type Subscores = z.infer<typeof SubscoresSchema>;
export type InvestorQuestion = z.infer<typeof InvestorQuestionSchema>;
export type PitchAnnotation = z.infer<typeof PitchAnnotationSchema>;
export type DealContext = z.infer<typeof DealContextSchema>;
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
