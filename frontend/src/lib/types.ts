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

export const NodeLatencySchema = z.object({
  node: z.string(),
  runs: z.number(),
  total_ms: z.number(),
});

export const RunTelemetrySchema = z.object({
  agent_count: z.number(),
  duration_ms: z.number(),
  llm_calls: z.number(),
  prompt_tokens: z.number(),
  completion_tokens: z.number(),
  search_calls: z.number(),
  failed_searches: z.number(),
  llm_cost_usd: z.number(),
  search_cost_usd: z.number(),
  total_cost_usd: z.number(),
  budget_usd: z.number(),
  budget_exit_reason: z.string().nullish(),
  nodes: z.array(NodeLatencySchema),
  pricing_as_of: z.string(),
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
  telemetry: RunTelemetrySchema.nullish(),
});

export const PlannerEventSchema = z.object({
  queries: z.array(z.string()),
  queryCount: z.number(),
});

export const RunEventSchema = z.object({
  runId: z.string(),
  attempt: z.number(),
  retriesLeft: z.number(),
  budgetUsd: z.number(),
});

export const EvidenceEventSchema = z.object({
  round: z.number(),
  query: z.string(),
  status: z.enum(["ok", "error"]),
  error: z.string().nullable(),
  items: z.array(z.object({ title: z.string(), url: z.string() })),
});

export const ScoutEventSchema = z.object({
  evidenceCount: z.number(),
  searches: z.number().optional(),
  failedSearches: z.number().optional(),
});

export const CriticEventSchema = z.object({
  iteration: z.number(),
  isValidated: z.boolean(),
  coverageScore: z.number().nullable(),
  feedback: z.string(),
  budgetExitReason: z.string().nullish(),
  iterationCapReached: z.boolean().optional(),
});

export const ErrorEventSchema = z.object({
  message: z.string(),
  node: z.string().nullish(),
  kind: z.enum(["upstream_api", "bad_model_output", "internal", "http", "network"]).optional(),
  retryable: z.boolean().optional(),
  runId: z.string().nullish(),
});

export const CancelledEventSchema = z.object({
  runId: z.string(),
  node: z.string(),
});

export const CancelResponseSchema = z.object({
  runId: z.string(),
  status: z.literal("cancelling"),
});

export const WriterEventSchema = z.object({
  memoReady: z.boolean(),
});

export const ShareSealSchema = z.object({
  generated_at: z.string(),
  signature: z.string(),
});

export const CitationAuditEventSchema = z.object({
  memo: MemoOutputSchema,
  seal: ShareSealSchema.optional(),
});

export const AnalysisModeSchema = z.enum(["market_scan", "pitch_lab"]);

export const SharedMemoSchema = z.object({
  pitch: z.string(),
  mode: AnalysisModeSchema,
  generated_at: z.string(),
  memo: MemoOutputSchema,
});

export const ShareViewSchema = z.object({
  share_id: z.string(),
  kind: z.enum(["memo", "compare"]),
  created_at: z.string(),
  memos: z.array(SharedMemoSchema).min(1),
});

export const ShareCreatedSchema = z.object({
  share_id: z.string(),
  created_at: z.string(),
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

export const RunRecordSchema = z.object({
  runId: z.string(),
  timestamp: z.number(),
  durationMs: z.number(),
  mode: z.string(),
  pitchScore: z.number().nullable(),
  iterations: z.number(),
  evidenceCount: z.number(),
  status: z.string(),
  costUsd: z.number().nullable(),
  promptTokens: z.number().nullable(),
  completionTokens: z.number().nullable(),
  llmCalls: z.number().nullable(),
  searchCalls: z.number().nullable(),
  nodeMs: z.record(z.string(), z.number()),
  budgetExitReason: z.string().nullable(),
});

export const MetricsSchema = z.object({
  totalRuns: z.number(),
  totalErrors: z.number(),
  avgDurationMs: z.number(),
  avgScore: z.number(),
  avgIterations: z.number(),
  avgEvidence: z.number(),
  totalCostUsd: z.number(),
  avgCostUsd: z.number(),
  avgTokensPerRun: z.number(),
  avgNodeMs: z.record(z.string(), z.number()),
  budgetExits: z.number(),
  modeBreakdown: z.record(z.string(), z.number()),
  scoreDistribution: z.object({ low: z.number(), mid: z.number(), high: z.number() }),
  recentRuns: z.array(RunRecordSchema),
});

export const EvalLabelSchema = z.enum(["supported", "unsupported", "contradicted"]);
export const EvalModeSchema = z.enum(["heuristic", "llm"]);
export const CaseOriginSchema = z.enum(["seed-real", "seed-constructed", "feedback"]);

export const EvidenceSnippetSchema = z.object({
  source_url: z.string().nullable(),
  title: z.string(),
  text: z.string(),
});

export const LabelScoreSchema = z.object({
  label: EvalLabelSchema,
  total: z.number(),
  correct: z.number(),
  accuracy: z.number(),
});

export const EvalRunSummarySchema = z.object({
  run_id: z.string(),
  mode: EvalModeSchema,
  model: z.string().nullable(),
  started_at: z.string(),
  dataset_version: z.number(),
  case_count: z.number(),
  overall_accuracy: z.number(),
  labels: z.array(LabelScoreSchema),
  cost_usd: z.number(),
});

export const FailedCaseSchema = z.object({
  id: z.string(),
  origin: CaseOriginSchema,
  claim: z.string(),
  pitch_excerpt: z.string(),
  evidence: z.array(EvidenceSnippetSchema),
  expected: EvalLabelSchema,
  predicted: EvalLabelSchema,
  detail: z.string(),
  downgraded_from: EvalLabelSchema.nullable(),
  notes: z.string(),
});

export const LatestEvalRunSchema = EvalRunSummarySchema.extend({
  failures: z.array(FailedCaseSchema),
});

export const EvalSummarySchema = z.object({
  generated_at: z.string(),
  dataset: z.object({
    name: z.string(),
    version: z.number(),
    updated: z.string(),
    case_count: z.number(),
    label_counts: z.record(EvalLabelSchema, z.number()),
    origin_counts: z.record(z.string(), z.number()),
    candidate_count: z.number(),
  }),
  baseline: z
    .object({
      run_id: z.string(),
      mode: EvalModeSchema,
      dataset_version: z.number(),
      case_count: z.number(),
      overall_accuracy: z.number(),
      labels: z.array(LabelScoreSchema),
    })
    .nullable(),
  latest_heuristic: LatestEvalRunSchema.nullable(),
  latest_llm: LatestEvalRunSchema.nullable(),
  history: z.array(EvalRunSummarySchema),
});

export const UserVerdictSchema = z.enum(["correct", "wrong"]);
export const ReviewStatusSchema = z.enum(["pending", "accepted", "rejected"]);

export const FeedbackCreatedSchema = z.object({
  feedback_id: z.number(),
  verified: z.boolean(),
});

export const FeedbackRecordSchema = z.object({
  feedback_id: z.number(),
  created_at: z.string(),
  origin: z.enum(["live", "demo"]),
  verified: z.boolean(),
  mode: AnalysisModeSchema,
  pitch_excerpt: z.string(),
  claim: z.string(),
  evidence_quote: z.string().nullable(),
  evidence_url: z.string().nullable(),
  model_verdict: z.string(),
  downgraded_from: z.string().nullable(),
  user_verdict: UserVerdictSchema,
  status: ReviewStatusSchema,
  gold_label: EvalLabelSchema.nullable(),
  reviewer_note: z.string(),
  reviewed_at: z.string().nullable(),
  exported_at: z.string().nullable(),
});

export const FeedbackListSchema = z.object({
  counts: z.object({
    total: z.number(),
    disagreements: z.number(),
    pending: z.number(),
    accepted: z.number(),
    rejected: z.number(),
    exported: z.number(),
  }),
  records: z.array(FeedbackRecordSchema),
});

export type UserVerdict = z.infer<typeof UserVerdictSchema>;
export type FeedbackRecord = z.infer<typeof FeedbackRecordSchema>;
export type FeedbackList = z.infer<typeof FeedbackListSchema>;
export type EvalLabel = z.infer<typeof EvalLabelSchema>;
export type EvalRunSummary = z.infer<typeof EvalRunSummarySchema>;
export type LatestEvalRun = z.infer<typeof LatestEvalRunSchema>;
export type FailedCase = z.infer<typeof FailedCaseSchema>;
export type EvalSummary = z.infer<typeof EvalSummarySchema>;
export type RunRecord = z.infer<typeof RunRecordSchema>;
export type Metrics = z.infer<typeof MetricsSchema>;
export type DemoRun = z.infer<typeof DemoRunSchema>;
export type RunSource = { kind: "demo"; recordedAt: string } | { kind: "live" } | { kind: "shared"; generatedAt: string };
export type ShareSeal = z.infer<typeof ShareSealSchema>;
export type SharedMemo = z.infer<typeof SharedMemoSchema>;
export type ShareView = z.infer<typeof ShareViewSchema>;
export type AnalysisMode = z.infer<typeof AnalysisModeSchema>;
export type Citation = z.infer<typeof CitationSchema>;
export type Groundedness = z.infer<typeof GroundednessSchema>;
export type RunTelemetry = z.infer<typeof RunTelemetrySchema>;
export type MarketCompetitor = z.infer<typeof MarketCompetitorSchema>;
export type Subscores = z.infer<typeof SubscoresSchema>;
export type InvestorQuestion = z.infer<typeof InvestorQuestionSchema>;
export type PitchAnnotation = z.infer<typeof PitchAnnotationSchema>;
export type DealContext = z.infer<typeof DealContextSchema>;
export type MemoOutput = z.infer<typeof MemoOutputSchema>;
export type RunEvent = z.infer<typeof RunEventSchema>;
export type EvidenceEvent = z.infer<typeof EvidenceEventSchema>;
export type PlannerEvent = z.infer<typeof PlannerEventSchema>;
export type ScoutEvent = z.infer<typeof ScoutEventSchema>;
export type CriticEvent = z.infer<typeof CriticEventSchema>;
export type WriterEvent = z.infer<typeof WriterEventSchema>;
export type CitationAuditEvent = z.infer<typeof CitationAuditEventSchema>;
export type ErrorEvent = z.infer<typeof ErrorEventSchema>;
export type CancelledEvent = z.infer<typeof CancelledEventSchema>;

export type AgentEvent =
  | { type: "run"; data: RunEvent }
  | { type: "planner"; data: PlannerEvent }
  | { type: "evidence"; data: EvidenceEvent }
  | { type: "scout"; data: ScoutEvent }
  | { type: "critic"; data: CriticEvent }
  | { type: "writer"; data: WriterEvent }
  | { type: "citation_audit"; data: CitationAuditEvent }
  | { type: "cancelled"; data: CancelledEvent }
  | { type: "error"; data: ErrorEvent };
