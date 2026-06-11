export interface ClinicalNoteResponse {
  id: string;
  patient_id: string;
  subjective: string;
  objective: string;
  assessment: string;
  plan: string;
  doctor_signed: boolean;
  signed_at: string | null;
  created_at: string;
}

export interface GenerateNoteRequest {
  patient_id: string;
  triage_result_id: string;
  transcript?: string;
  doctor_additions?: string;
}

export interface SignNoteRequest {
  doctor_id: string;
}

export interface GenerateReferralRequest {
  clinical_note_id: string;
  receiving_facility: string;
  reason: string;
}

export interface ReferralResponse {
  id: string;
  patient_id: string;
  clinical_note_id: string;
  receiving_facility: string;
  reason: string;
  body: string;
  created_at: string;
}

export interface GenerateDischargeRequest {
  clinical_note_id: string;
  medications: string[];
  follow_up?: string;
}

export interface DischargeResponse {
  id: string;
  patient_id: string;
  diagnosis: string;
  medications: string[];
  instructions: string;
  follow_up: string | null;
  created_at: string;
}