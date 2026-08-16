"use client";

import { useState, useEffect } from "react";
import { subscribeResearchStream } from "../lib/sse/research-stream";
import { JobStatus } from "../lib/types/api";

export function useResearchStream(jobId: string | null) {
  const [status, setStatus] = useState<JobStatus>("queued");
  const [currentStep, setCurrentStep] = useState<string | null>(null);
  const [completedSteps, setCompletedSteps] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!jobId) return;

    const unsubscribe = subscribeResearchStream(jobId, {
      onQueued: () => {
        setStatus("queued");
        setCurrentStep(null);
        setCompletedSteps([]);
      },
      onProgress: (payload) => {
        setStatus("running");
        setCurrentStep(payload.current_step);
        setCompletedSteps(payload.completed_steps);
      },
      onCompleted: (payload) => {
        setStatus("completed");
        setCurrentStep(payload.current_step);
        setCompletedSteps(payload.completed_steps);
      },
      onFailed: (payload, err) => {
        setStatus("failed");
        setError(err);
      }
    });

    return () => unsubscribe();
  }, [jobId]);

  return { status, currentStep, completedSteps, error };
}
