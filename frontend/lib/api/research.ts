"use client";

import { apiFetch } from "./client";
import {
  ResearchJobResponse,
  ResearchStatusResponse,
  ResearchProgressResponse,
  ResearchRequest,
  ResearchHistoryResponse,
} from "../types/api";

/** Start a research job. Returns the created job id (HTTP 202). */
export function submitResearch(
  query: string,
  signal?: AbortSignal
): Promise<ResearchJobResponse> {
  const body: ResearchRequest = { query };
  return apiFetch<ResearchJobResponse>("/research", {
    method: "POST",
    body: JSON.stringify(body),
    signal,
  });
}

/** Get the current status/result of a research job (404 if unknown/expired). */
export function getJobStatus(
  jobId: string,
  signal?: AbortSignal
): Promise<ResearchStatusResponse> {
  return apiFetch<ResearchStatusResponse>(`/research/${encodeURIComponent(jobId)}`, {
    signal,
  });
}

/** Get the live progress snapshot of a research job. */
export function getJobProgress(
  jobId: string,
  signal?: AbortSignal
): Promise<ResearchProgressResponse> {
  return apiFetch<ResearchProgressResponse>(
    `/research/${encodeURIComponent(jobId)}/progress`,
    { signal }
  );
}

/** Get the authenticated user's research history (newest first). */
export function getResearchHistory(
  signal?: AbortSignal
): Promise<ResearchHistoryResponse> {
  return apiFetch<ResearchHistoryResponse>("/research/history", { signal });
}
