export interface EvalScoreItem {
  span_id: string;
  relevance: number;
  completeness: number;
  ranking: number;
  safety: number;
  composite: number;
  reasoning: string;
  below_threshold: boolean;
  evaluated_at: string;
}

export interface FailurePatternItem {
  pattern_id: string;
  description: string;
  affected_span_count: number;
  suggested_fix: string;
}

export interface PromptImprovementResponse {
  prompt_name: string;
  previous_version_id: string | null;
  new_version_content: string;
  failure_patterns: string[];
  rolling_avg_score: number;
  created_at: string;
}

export interface EvalRunResponse {
  scores: EvalScoreItem[];
  failure_patterns: FailurePatternItem[];
  rolling_avg_score: number;
  improvement_triggered: boolean;
  improvement: PromptImprovementResponse | null;
}