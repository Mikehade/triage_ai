import { http } from "./http";
import type { EvalRunResponse } from "../core/entities/evaluation";

export const evaluationService = {
  run: (hours = 24): Promise<EvalRunResponse> =>
    http.post<EvalRunResponse>(`/eval/run?hours=${hours}`),

  getPrompt: (promptName: string) =>
    http.get(`/eval/debug/prompt/${promptName}`),
};