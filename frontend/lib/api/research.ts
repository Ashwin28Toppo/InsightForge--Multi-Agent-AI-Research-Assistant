"use client";

import { apiFetch } from "./client";
import {
  ResearchJobResponse,
  ResearchStatusResponse,
  ResearchProgressResponse,
  ResearchRequest,
  ResearchHistoryResponse,
} from "../types/api";

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

export function getJobStatus(
  jobId: string,
  signal?: AbortSignal
): Promise<ResearchStatusResponse> {
  return apiFetch<ResearchStatusResponse>(`/research/${encodeURIComponent(jobId)}`, {
    signal,
  });
}

export function getJobProgress(
  jobId: string,
  signal?: AbortSignal
): Promise<ResearchProgressResponse> {
  return apiFetch<ResearchProgressResponse>(
    `/research/${encodeURIComponent(jobId)}/progress`,
    { signal }
  );
}

export function getResearchHistory(
  signal?: AbortSignal
): Promise<ResearchHistoryResponse> {
  return apiFetch<ResearchHistoryResponse>("/research/history", { signal });
}
