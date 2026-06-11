import { http } from "./http";
import type {
  GenerateNoteRequest,
  ClinicalNoteResponse,
  SignNoteRequest,
  GenerateReferralRequest,
  ReferralResponse,
  GenerateDischargeRequest,
  DischargeResponse,
} from "../core/entities/consult";

export const consultService = {
  generateNote: (payload: GenerateNoteRequest): Promise<ClinicalNoteResponse> =>
    http.post<ClinicalNoteResponse>("/consult/note", payload),

  signNote: (noteId: string, payload: SignNoteRequest): Promise<ClinicalNoteResponse> =>
    http.post<ClinicalNoteResponse>(`/consult/note/${noteId}/sign`, payload),

  generateReferral: (payload: GenerateReferralRequest): Promise<ReferralResponse> =>
    http.post<ReferralResponse>("/consult/referral", payload),

  generateDischarge: (payload: GenerateDischargeRequest): Promise<DischargeResponse> =>
    http.post<DischargeResponse>("/consult/discharge", payload),
};