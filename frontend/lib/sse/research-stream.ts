"use client";

import { SseProgressPayload } from "../types/api";

interface StreamHandlers {
  onQueued?: (payload: SseProgressPayload) => void;
  onProgress?: (payload: SseProgressPayload) => void;
  onCompleted?: (payload: SseProgressPayload) => void;
  onFailed?: (payload: SseProgressPayload, error: string) => void;
  onReconnect?: () => void;
}

export function subscribeResearchStream(
  jobId: string,
  handlers: StreamHandlers
): () => void {
  // NOTE: Real integration will use native EventSource:
  // const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";
  // const source = new EventSource(`${BASE_URL}/research/${jobId}/stream`);
  // ...
  // return () => source.close();

  console.log(`Subscribed mock stream for job: ${jobId}`);

  // Simulate progress events for testing the timeline visual state
  const mockQueuedTimeout = setTimeout(() => {
    handlers.onQueued?.({
      job_id: jobId,
      status: "queued",
      current_step: null,
      completed_steps: []
    });
  }, 500);

  const mockProgressTimeout = setTimeout(() => {
    handlers.onProgress?.({
      job_id: jobId,
      status: "running",
      current_step: "research",
      completed_steps: ["plan"]
    });
  }, 2000);

  const mockCompletedTimeout = setTimeout(() => {
    handlers.onCompleted?.({
      job_id: jobId,
      status: "completed",
      current_step: "writer",
      completed_steps: ["plan", "research", "evidence", "claim_extraction", "fact_check", "citation", "confidence", "writer"]
    });
  }, 6000);

  // Return unsubscribe cleanup handler
  return () => {
    console.log(`Unsubscribed mock stream for job: ${jobId}`);
    clearTimeout(mockQueuedTimeout);
    clearTimeout(mockProgressTimeout);
    clearTimeout(mockCompletedTimeout);
  };
}
