export type Citation = {
  id: string;
  source: string;
  title: string;
  url: string;
  snippet: string;
  section: string;
};

export type Message = {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  citations?: Citation[];
  confidence?: number;
  sources_used?: string[];
  error?: boolean;
};

export type ArticlePreview = {
  pmid: string;
  title: string;
  authors: string[];
  journal: string;
  publicationDate: string;
  abstract: string;
  url: string;
  credibility: 'High' | 'Medium' | 'Low';
  confidence: number;
};

export type QueryResponse = {
  answer: string;
  confidence_score: number;
  citations: Array<Record<string, unknown>>;
  request_id?: string | null;
  trace_id?: string | null;
  conversation_id?: string | null;
  sources_used?: string[];
};

export type AppConfig = {
  llm_configured: boolean;
  llm_model: string;
  trusted_sources: string[];
  app_name: string;
  version: string;
};

export type ConfidenceBucket = {
  label: string;
  count: number;
  min_score: number;
  max_score: number;
};

export type SourceCoverageItem = {
  source_name: string;
  coverage_rate: number;
  evidence_count: number;
  hallucination_rate: number;
};

export type MetricPoint = {
  timestamp: string;
  value: number;
};

export type EvaluationDashboard = {
  hallucination_rate: number;
  citation_accuracy: number;
  retrieval_precision: number;
  source_coverage: number;
  confidence_distribution: ConfidenceBucket[];
  confidence_level_counts: Record<string, number>;
  source_coverage_breakdown: SourceCoverageItem[];
  confidence_trend: MetricPoint[];
  citation_accuracy_trend: MetricPoint[];
  retrieval_precision_trend: MetricPoint[];
  generated_at: string;
  total_runs: number;
  total_sessions: number;
};

export type ApiError = {
  error: {
    code: string;
    message: string;
    details: unknown[];
    request_id?: string | null;
  };
  status_code: number;
};

export interface ConversationSummary {
  id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface ConversationDetail {
  id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
  messages: ConversationMessage[];
}

export interface ConversationMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  confidence_score?: number | null;
  citations?: Citation[] | null;
  sources_used?: string[] | null;
  created_at: string;
}

export interface ConversationListResponse {
  conversations: ConversationSummary[];
  total: number;
}
