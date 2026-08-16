"use client";

import { apiFetch } from "./client";
import {
  ResearchJobResponse,
  ResearchStatusResponse,
  ResearchProgressResponse,
  ResearchRequest,
} from "../types/api";

/** Start a research job. Returns the created job id (HTTP 202). */
export function submitResearch(query: string): Promise<ResearchJobResponse> {
  const body: ResearchRequest = { query };
  return apiFetch<ResearchJobResponse>("/research", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

/** Get the current status/result of a research job (404 if unknown/expired). */
export function getJobStatus(jobId: string): Promise<ResearchStatusResponse> {
  return apiFetch<ResearchStatusResponse>(`/research/${encodeURIComponent(jobId)}`);
}

/** Get the live progress snapshot of a research job. */
export function getJobProgress(jobId: string): Promise<ResearchProgressResponse> {
  return apiFetch<ResearchProgressResponse>(
    `/research/${encodeURIComponent(jobId)}/progress`
  );
}
