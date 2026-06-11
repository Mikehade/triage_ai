import type { UrgencyLevel } from "../entities/triage";
import type { TriageStatus } from "../entities/patient";

export const URGENCY_LABELS: Record<UrgencyLevel, string> = {
  1: "Routine",
  2: "Low",
  3: "Moderate",
  4: "High",
  5: "Critical",
};

export const URGENCY_COLORS: Record<UrgencyLevel, string> = {
  1: "urgency-routine",
  2: "urgency-low",
  3: "urgency-moderate",
  4: "urgency-high",
  5: "urgency-critical",
};

export const TRIAGE_STATUS_COLORS: Record<TriageStatus, string> = {
  pending:         "var(--text-muted)",
  triaged:         "var(--accent)",
  in_consultation: "var(--urgency-3)",
  documented:      "var(--success)",
  referred:        "#a78bfa",
  discharged:      "var(--text-muted)",
};

export const TRIAGE_STATUS_LABELS: Record<TriageStatus, string> = {
  pending:         "Pending",
  triaged:         "Triaged",
  in_consultation: "In Consultation",
  documented:      "Documented",
  referred:        "Referred",
  discharged:      "Discharged",
};

export const shouldFlag = (level: UrgencyLevel): boolean => level >= 4;
export const EVAL_SCORE_THRESHOLD = 7.0;
export const POLL_INTERVAL_MS = 3000;
export const POLL_TIMEOUT_MS = 60000;