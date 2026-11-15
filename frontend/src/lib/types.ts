import { z } from "zod";

export const CitationSchema = z.object({
  quote: z.string(),
  source_url: z.string(),
  retrieved_at: z.string(),
});

export const MarketCompetitorSchema = z.object({
  competitor: z.string(),
  pricing: z.string(),
  funding: z.string(),
  citation: CitationSchema.nullish(),
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
  citation: CitationSchema.nullish(),
  downgraded_from: z.string().nullish(),
});

export const GroundednessSchema = z.object({
  cited_claims: z.number(),
  total_claims: z.number(),
  downgraded_claims: z.number(),
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
  groundedness: GroundednessSchema.nullish(),
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
  memoReady: z.boolean(),
});

export const CitationAuditEventSchema = z.object({
  memo: MemoOutputSchema,
});

export const DemoRunSchema = z.object({
  id: z.string(),
  category: z.string(),
  title: z.string(),
  tagline: z.string(),
  pitch: z.string(),
  mode: z.enum(["market_scan", "pitch_lab"]),
  recordedAt: z.string(),
  durationMs: z.number(),
  events: z.array(
    z.object({
      event: z.string(),
      atMs: z.number(),
      data: z.unknown(),
    })
  ),
});

export type DemoRun = z.infer<typeof DemoRunSchema>;
export type RunSource = { kind: "demo"; recordedAt: string } | { kind: "live" };
export type Citation = z.infer<typeof CitationSchema>;
export type Groundedness = z.infer<typeof GroundednessSchema>;
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
export type CitationAuditEvent = z.infer<typeof CitationAuditEventSchema>;

export type AgentEvent =
  | { type: "planner"; data: PlannerEvent }
  | { type: "scout"; data: ScoutEvent }
  | { type: "critic"; data: CriticEvent }
  | { type: "writer"; data: WriterEvent }
  | { type: "citation_audit"; data: CitationAuditEvent }
  | { type: "error"; data: { message: string } };
