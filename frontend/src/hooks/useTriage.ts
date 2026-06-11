import { useState, useCallback, useEffect, useRef } from "react";
import { triageService } from "../services/triage.service";
import type { BriefResponse, TriageResultResponse } from "../core/entities/triage";
import { ApiError } from "../services/http";
import { POLL_INTERVAL_MS, POLL_TIMEOUT_MS } from "../core/constants/urgency";

// ─── Auto-loading brief with polling ─────────────────────────────────────────

type BriefState = "idle" | "loading" | "polling" | "ready" | "timeout" | "error";

interface UseBriefReturn {
  brief: BriefResponse | null;
  state: BriefState;
  error: string | null;
  fetchBrief: (patientId: string) => void;
  runTriageThenPoll: (patientId: string) => Promise<void>;
}

export function useBrief(): UseBriefReturn {
  const [brief, setBrief] = useState<BriefResponse | null>(null);
  const [state, setState] = useState<BriefState>("idle");
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const stopPolling = useCallback(() => {
    if (pollRef.current) clearInterval(pollRef.current);
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
  }, []);

  useEffect(() => () => stopPolling(), [stopPolling]);

  // Try to get brief — if 404 start polling
  const fetchBrief = useCallback(
    (patientId: string) => {
      stopPolling();
      setState("loading");
      setError(null);

      triageService
        .getBrief(patientId)
        .then((data) => {
          setBrief(data);
          setState("ready");
        })
        .catch((err) => {
          if (err instanceof ApiError && err.status === 404) {
            // Triage not yet done — start polling
            setState("polling");
            pollRef.current = setInterval(async () => {
              try {
                const data = await triageService.getBrief(patientId);
                stopPolling();
                setBrief(data);
                setState("ready");
              } catch {
                // still 404, keep polling
              }
            }, POLL_INTERVAL_MS);

            timeoutRef.current = setTimeout(() => {
              stopPolling();
              setState("timeout");
            }, POLL_TIMEOUT_MS);
          } else {
            setState("error");
            setError(
              err instanceof ApiError ? err.detail.message : "Failed to load brief"
            );
          }
        });
    },
    [stopPolling]
  );

  // Run triage pipeline first, then poll for brief
  const runTriageThenPoll = useCallback(
    async (patientId: string) => {
      stopPolling();
      setState("loading");
      setError(null);
      try {
        await triageService.run(patientId);
        fetchBrief(patientId);
      } catch (err) {
        setState("error");
        setError(
          err instanceof ApiError ? err.detail.message : "Triage failed"
        );
      }
    },
    [fetchBrief, stopPolling]
  );

  return { brief, state, error, fetchBrief, runTriageThenPoll };
}