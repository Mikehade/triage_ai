export type UrgencyLevel = 1 | 2 | 3 | 4 | 5;
export type DrugSeverity = "mild" | "moderate" | "severe";

export interface DifferentialItem {
  rank: number;
  condition: string;
  confidence: number;
  reasoning: string;
  distinguishing_questions: string[];
  icd10_code: string | null;
}

export interface DrugFlagItem {
  drug_a: string;
  drug_b: string;
  severity: DrugSeverity;
  description: string;
  recommendation: string;
}

export interface TriageResultResponse {
  id: string;
  patient_id: string;
  intake_id: string;
  urgency_level: UrgencyLevel;
  urgency_label: string;
  urgency_reasoning: string;
  red_flags: string[];
  differentials: DifferentialItem[];
  drug_flags: DrugFlagItem[];
  grounding_sources: string[];
  computed_at: string;
}

export interface BriefResponse {
  id: string;
  patient_id: string;
  urgency_level: UrgencyLevel;
  urgency_label: string;
  summary: string;
  top_differentials: string[];
  drug_flag_summary: string | null;
  red_flags: string[];
  suggested_questions: string[];
  improvement_notes: string | null;
  assembled_at: string;
}