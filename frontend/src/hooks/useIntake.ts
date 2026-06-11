import { useState, useCallback, useEffect, useRef } from "react";
import { intakeService } from "../services/intake.service";
import { triageService } from "../services/triage.service";
import type {
  IntakeRequest,
  IntakeResponse,
  PatientSummary,
  PatientDetail,
  PaginatedPatientsResponse,
} from "../core/entities/patient";
import type { TriageResultResponse } from "../core/entities/triage";
import { ApiError } from "../services/http";

// ─── Submit intake + run triage ───────────────────────────────────────────────

interface UseIntakeReturn {
  submitting: boolean;
  error: string | null;
  submitIntakeAndTriage: (
    payload: IntakeRequest
  ) => Promise<{ intake: IntakeResponse; triage: TriageResultResponse } | null>;
}

export function useIntake(): UseIntakeReturn {
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submitIntakeAndTriage = useCallback(
    async (payload: IntakeRequest) => {
      setSubmitting(true);
      setError(null);
      try {
        const intake = await intakeService.submit(payload);
        const patientId = intake.patient_id ?? intake.id;
        const triage = await triageService.run(patientId);
        return { intake, triage };
      } catch (err) {
        const msg =
          err instanceof ApiError ? err.detail.message : "Submission failed";
        setError(msg);
        return null;
      } finally {
        setSubmitting(false);
      }
    },
    []
  );

  return { submitting, error, submitIntakeAndTriage };
}

// ─── Debounced patient search ─────────────────────────────────────────────────

interface UsePatientSearchReturn {
  results: PatientSummary[];
  searching: boolean;
  search: (query: string) => void;
  clear: () => void;
}

export function usePatientSearch(): UsePatientSearchReturn {
  const [results, setResults] = useState<PatientSummary[]>([]);
  const [searching, setSearching] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const search = useCallback((query: string) => {
    if (timerRef.current) clearTimeout(timerRef.current);
    if (!query.trim()) {
      setResults([]);
      return;
    }
    timerRef.current = setTimeout(async () => {
      setSearching(true);
      try {
        const res = await intakeService.searchPatients(query);
        setResults(res.patients);
      } catch {
        setResults([]);
      } finally {
        setSearching(false);
      }
    }, 300);
  }, []);

  const clear = useCallback(() => {
    setResults([]);
    if (timerRef.current) clearTimeout(timerRef.current);
  }, []);

  useEffect(() => () => { if (timerRef.current) clearTimeout(timerRef.current); }, []);

  return { results, searching, search, clear };
}

// ─── Paginated patient list ───────────────────────────────────────────────────

interface UsePatientListReturn {
  data: PaginatedPatientsResponse | null;
  loading: boolean;
  error: string | null;
  page: number;
  goToPage: (p: number) => void;
  refetch: () => void;
}

export function usePatientList(): UsePatientListReturn {
  const [data, setData] = useState<PaginatedPatientsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    intakeService
      .listPatients(page)
      .then((res) => { if (!cancelled) setData(res); })
      .catch((err) => {
        if (!cancelled) {
          setError(
            err instanceof ApiError ? err.detail.message : "Failed to load patients"
          );
        }
      })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [page, tick]);

  const goToPage = useCallback((p: number) => setPage(p), []);
  const refetch = useCallback(() => setTick((t) => t + 1), []);

  return { data, loading, error, page, goToPage, refetch };
}

// ─── Single patient detail ────────────────────────────────────────────────────

interface UsePatientDetailReturn {
  patient: PatientDetail | null;
  loading: boolean;
  error: string | null;
}

export function usePatientDetail(patientId: string | null): UsePatientDetailReturn {
  const [patient, setPatient] = useState<PatientDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!patientId) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    intakeService
      .getPatient(patientId)
      .then((res) => { if (!cancelled) setPatient(res); })
      .catch((err) => {
        if (!cancelled) {
          setError(
            err instanceof ApiError ? err.detail.message : "Failed to load patient"
          );
        }
      })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [patientId]);

  return { patient, loading, error };
}