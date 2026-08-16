"use client";

import { ResearchJobResponse, ResearchStatusResponse, ResearchProgressResponse } from "../types/api";

export async function submitResearch(query: string): Promise<ResearchJobResponse> {
  // NOTE: Real integration will call apiFetch<ResearchJobResponse>("/research",
  // { method: "POST", body: JSON.stringify({ query }) }) from ./client.
  // Visual foundation: return a mock queued job referencing the query.
  const tag = query.trim().toLowerCase().replace(/\s+/g, "-").slice(0, 24) || "inquiry";
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve({
        job_id: `mock-${tag}-${crypto.randomUUID().slice(0, 8)}`,
        status: "queued"
      });
    }, 500);
  });
}

export async function getJobStatus(jobId: string): Promise<ResearchStatusResponse> {
  // For mock phase, return completed structure
  return new Promise((resolve) => {
    resolve({
      job_id: jobId,
      status: "completed",
      result: {
        query: "What are the latest advances in solid-state batteries electrolytes?",
        report: "Mock report completed.",
        confidence: "high"
      }
    });
  });
}

export async function getJobProgress(jobId: string): Promise<ResearchProgressResponse> {
  return new Promise((resolve) => {
    resolve({
      job_id: jobId,
      status: "running",
      current_step: "research",
      completed_steps: ["plan"]
    });
  });
}
