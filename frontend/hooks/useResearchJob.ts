"use client";

import { useState, useCallback, useEffect } from "react";
import { getJobStatus } from "../lib/api/research";
import { normalizeResearchResult } from "../lib/utils/normalize";
import { apiErrorMessage } from "../lib/utils/errors";
import type { ResearchResult, JobStatus } from "../lib/types/api";

/**
 * Job status/result. Fetches on mount and exposes refresh() — the workspace
 * calls refresh() when the SSE stream reports a terminal state to hydrate
 * the final result (or the authoritative error).
 */
export function useResearchJob(jobId: string | null) {
  const [status, setStatus] = useState<JobStatus>("queued");
  const [result, setResult] = useState<ResearchResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [notFound, setNotFound] = useState(false);
  const [requestId, setRequestId] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!jobId) return;
    setLoading(true);
    try {
      const res = await getJobStatus(jobId);
      setStatus(res.status);
      setNotFound(false);
      if (res.status === "failed") {
        setError(res.error || "Research job failed");
      } else if (res.status === "completed") {
        setError(null);
        setResult(res.result ? normalizeResearchResult(res.result) : null);
      }
    } catch (err) {
      const apiError = err as { status?: number; requestId?: string | null };
      if (apiError.status === 404) {
        setNotFound(true);
        setError("Research job not found or expired.");
      } else {
        setError(apiErrorMessage(err));
      }
      setRequestId(apiError.requestId ?? null);
    } finally {
      setLoading(false);
    }
  }, [jobId]);

  useEffect(() => {
    if (!jobId) return;
    // Defer to a microtask so no setState runs synchronously in the effect.
    void Promise.resolve().then(() => refresh());
  }, [jobId, refresh]);

  return {
    status,
    result,
    error,
    loading,
    notFound,
    requestId,
    refresh,
    isTerminal: status === "completed" || status === "failed",
  };
}
