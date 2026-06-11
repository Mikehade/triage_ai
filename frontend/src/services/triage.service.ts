import { http } from "./http";
import type { TriageResultResponse, BriefResponse } from "../core/entities/triage";

export const triageService = {
  run: (patientId: string): Promise<TriageResultResponse> =>
    http.post<TriageResultResponse>(`/triage/run/${patientId}`),

  getBrief: (patientId: string): Promise<BriefResponse> =>
    http.get<BriefResponse>(`/triage/brief/${patientId}`),
};