export type Sex = "male" | "female" | "other";

export type TriageStatus =
  | "pending"
  | "triaged"
  | "in_consultation"
  | "documented"
  | "referred"
  | "discharged";

export interface VitalsInput {
  temperature_celsius?: number;
  pulse_bpm?: number;
  systolic_bp?: number;
  diastolic_bp?: number;
  respiratory_rate?: number;
  oxygen_saturation?: number;
  weight_kg?: number;
  height_cm?: number;
}

// ─── Intake ───────────────────────────────────────────────────────────────────

export interface IntakeRequest {
  // Patient linking
  patient_id?: string | null;

  // New patient fields (required when patient_id is null)
  first_name?: string;
  last_name?: string;
  date_of_birth?: string;   // ISO date string e.g. "1990-01-15"
  phone_number?: string;

  // Clinical — age is computed from DOB, never shown as input
  age: number;
  sex: Sex;
  chief_complaint: string;
  symptom_duration_hours: number;
  current_medications: string[];
  allergies: string[];
  vitals?: VitalsInput;
  additional_history?: string;
}

export interface IntakeResponse {
  id: string;
  patient_id: string | null;
  age: number;
  sex: Sex;
  chief_complaint: string;
  symptom_duration_hours: number;
  current_medications: string[];
  allergies: string[];
  vitals: VitalsInput | null;
  additional_history: string | null;
  submitted_at: string;
}

// ─── Patient search / list ────────────────────────────────────────────────────

export interface PatientSummary {
  id: string;
  full_name: string;
  sex: Sex;
  date_of_birth: string;
  phone_number: string | null;
  triage_status: TriageStatus;
  created_at: string;
}

export interface PatientSearchResponse {
  patients: PatientSummary[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  query: string;
}

// ─── Triage embedded in patient list ─────────────────────────────────────────

export interface EmbeddedUrgency {
  level: 1 | 2 | 3 | 4 | 5;
  label: string;
  reasoning: string;
  red_flags: string[];
}

export interface EmbeddedTriageResult {
  id: string;
  urgency: EmbeddedUrgency;
  top_differentials: string[];
  computed_at: string;
}

export interface EmbeddedBrief {
  id: string;
  urgency_label: string;
  summary: string;
  top_differentials: string[];
  drug_flag_summary: string | null;
  red_flags: string[];
  suggested_questions: string[];
  assembled_at: string;
}

export interface PatientDetail extends PatientSummary {
  triage_result: EmbeddedTriageResult | null;
  brief: EmbeddedBrief | null;
}

export interface PaginatedPatientsResponse {
  patients: PatientDetail[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// ─── Utility ──────────────────────────────────────────────────────────────────

export function computeAge(dateOfBirth: string): number {
  const today = new Date();
  const dob = new Date(dateOfBirth);
  let age = today.getFullYear() - dob.getFullYear();
  const monthDiff = today.getMonth() - dob.getMonth();
  if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < dob.getDate())) {
    age--;
  }
  return age;
}

export function timeAgo(isoDate: string): string {
  const diff = Date.now() - new Date(isoDate).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}