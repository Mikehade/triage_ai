import { useState, useCallback } from "react";
import { evaluationService } from "../services/evaluation.service";
import type { EvalRunResponse } from "../core/entities/evaluation";
import { ApiError } from "../services/http";

interface UseEvaluationReturn {
  result: EvalRunResponse | null;
  loading: boolean;
  error: string | null;
  runEval: (hours?: number) => Promise<void>;
}

export function useEvaluation(): UseEvaluationReturn {
  const [result, setResult] = useState<EvalRunResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runEval = useCallback(async (hours = 24) => {
    setLoading(true);
    setError(null);
    try {
      const data = await evaluationService.run(hours);
      setResult(data);
    } catch (err) {
      const msg = err instanceof ApiError ? err.detail.message : "Evaluation failed";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  return { result, loading, error, runEval };
}