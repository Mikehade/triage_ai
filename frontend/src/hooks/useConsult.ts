import { useState, useCallback } from "react";
import { consultService } from "../services/consult.service";
import type {
  ClinicalNoteResponse,
  GenerateNoteRequest,
  GenerateReferralRequest,
  ReferralResponse,
  GenerateDischargeRequest,
  DischargeResponse,
} from "../core/entities/consult";
import { ApiError } from "../services/http";

interface UseConsultReturn {
  note: ClinicalNoteResponse | null;
  referral: ReferralResponse | null;
  discharge: DischargeResponse | null;
  loading: boolean;
  error: string | null;
  generateNote: (payload: GenerateNoteRequest) => Promise<void>;
  signNote: (noteId: string, doctorId: string) => Promise<void>;
  generateReferral: (payload: GenerateReferralRequest) => Promise<void>;
  generateDischarge: (payload: GenerateDischargeRequest) => Promise<void>;
}

export function useConsult(): UseConsultReturn {
  const [note, setNote] = useState<ClinicalNoteResponse | null>(null);
  const [referral, setReferral] = useState<ReferralResponse | null>(null);
  const [discharge, setDischarge] = useState<DischargeResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const withLoading = useCallback(async (fn: () => Promise<void>) => {
    setLoading(true);
    setError(null);
    try {
      await fn();
    } catch (err) {
      const msg =
        err instanceof ApiError ? err.detail.message : "Request failed";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  const generateNote = useCallback(
    (payload: GenerateNoteRequest) =>
      withLoading(async () => {
        const data = await consultService.generateNote(payload);
        setNote(data);
      }),
    [withLoading]
  );

  const signNote = useCallback(
    (noteId: string, doctorId: string) =>
      withLoading(async () => {
        const data = await consultService.signNote(noteId, {
          doctor_id: doctorId,
        });
        setNote(data);
      }),
    [withLoading]
  );

  const generateReferral = useCallback(
    (payload: GenerateReferralRequest) =>
      withLoading(async () => {
        const data = await consultService.generateReferral(payload);
        setReferral(data);
      }),
    [withLoading]
  );

  const generateDischarge = useCallback(
    (payload: GenerateDischargeRequest) =>
      withLoading(async () => {
        const data = await consultService.generateDischarge(payload);
        setDischarge(data);
      }),
    [withLoading]
  );

  return {
    note,
    referral,
    discharge,
    loading,
    error,
    generateNote,
    signNote,
    generateReferral,
    generateDischarge,
  };
}