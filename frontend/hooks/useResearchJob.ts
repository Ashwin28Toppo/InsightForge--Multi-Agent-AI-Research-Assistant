"use client";

import { useState, useEffect } from "react";
import { getJobStatus } from "../lib/api/research";
import { ResearchResult, JobStatus } from "../lib/types/api";

export function useResearchJob(jobId: string | null) {
  const [status, setStatus] = useState<JobStatus>("queued");
  const [result, setResult] = useState<ResearchResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!jobId) return;
    // Capture in a const so TypeScript narrows it inside the async closure.
    const id = jobId;
    let cancelled = false;

    async function fetchJob() {
      setLoading(true);
      try {
        const res = await getJobStatus(id);
        if (cancelled) return;
        setStatus(res.status);
        if (res.result) {
          setResult(res.result);
        }
        if (res.error) {
          setError(res.error);
        }
      } catch (err) {
        if (cancelled) return;
        setError(
          err instanceof Error ? err.message : "Failed to fetch research job status"
        );
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    fetchJob();
    return () => {
      cancelled = true;
    };
  }, [jobId]);

  return { status, result, error, loading };
}
