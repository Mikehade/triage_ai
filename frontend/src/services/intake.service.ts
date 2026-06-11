import { http } from "./http";
import type {
  IntakeRequest,
  IntakeResponse,
  PatientSearchResponse,
  PaginatedPatientsResponse,
  PatientDetail,
} from "../core/entities/patient";

export const intakeService = {
  submit: (payload: IntakeRequest): Promise<IntakeResponse> =>
    http.post<IntakeResponse>("/intake/", payload),

  searchPatients: (query: string): Promise<PatientSearchResponse> =>
    http.get<PatientSearchResponse>(
      `/intake/patients/search?q=${encodeURIComponent(query)}&page=1&page_size=50`
    ),

  listPatients: (
    page = 1,
    pageSize = 50
  ): Promise<PaginatedPatientsResponse> =>
    http.get<PaginatedPatientsResponse>(
      `/intake/patients?page=${page}&page_size=${pageSize}&include_triage=true&include_brief=true`
    ),

  getPatient: (patientId: string): Promise<PatientDetail> =>
    http.get<PatientDetail>(
      `/intake/patients/${patientId}?include_triage=true&include_brief=true`
    ),
};