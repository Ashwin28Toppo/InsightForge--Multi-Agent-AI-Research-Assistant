"use client";

import { useState, useEffect, useRef } from "react";
import { subscribeResearchStream } from "../lib/sse/research-stream";
import { getJobProgress } from "../lib/api/research";
import type {
  JobStatus,
  ResearchProgressResponse,
  ConnectionState,
} from "../lib/types/api";

const PROGRESS_POLL_MS = 4000;

/**
 * Live research progress: SSE is the primary channel; a progress-endpoint
 * poll runs only while the SSE connection is not open (fallback/recovery).
 * Polling stops once the job reaches a terminal state. Never POSTs.
 */
export function useResearchStream(jobId: string | null) {
  const [status, setStatus] = useState<JobStatus>("queued");
  const [currentStep, setCurrentStep] = useState<string | null>(null);
  const [completedSteps, setCompletedSteps] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [connection, setConnection] = useState<ConnectionState>("connecting");
  const [reconnectAttempt, setReconnectAttempt] = useState(0);

  const connectionRef = useRef<ConnectionState>("connecting");
  const setConn = (next: ConnectionState) => {
    connectionRef.current = next;
    setConnection(next);
  };

  useEffect(() => {
    if (!jobId) return;
    const id = jobId;
    let cancelled = false;
    let terminal = false;
    let pollTimer: ReturnType<typeof setInterval> | null = null;
    let unsubscribe: () => void = () => {};

    const applyProgress = (p: ResearchProgressResponse) => {
      setStatus(p.status);
      setCurrentStep(p.current_step ?? null);
      setCompletedSteps(
        Array.isArray(p.completed_steps) ? p.completed_steps : []
      );
      if (p.status === "completed" || p.status === "failed") {
        terminal = true;
      }
    };

    const stopPolling = () => {
      if (pollTimer) {
        clearInterval(pollTimer);
        pollTimer = null;
      }
    };

    const startPolling = () => {
      if (pollTimer || terminal) return;
      pollTimer = setInterval(async () => {
        if (cancelled || terminal) return;
        if (connectionRef.current === "open") return; // SSE healthy — don't hammer
        try {
          const p = await getJobProgress(id);
          if (cancelled) return;
          applyProgress(p);
          if (terminal) stopPolling();
        } catch (err) {
          // 404 = job unknown/expired: stop polling and close the stream.
          if ((err as { status?: number }).status === 404 && !terminal) {
            terminal = true;
            stopPolling();
            setStatus("failed");
            setError("Research job not found or expired.");
            setConn("closed");
            unsubscribe();
          }
          // Other errors are transient; SSE or the next poll recovers.
        }
      }, PROGRESS_POLL_MS);
    };

    unsubscribe = subscribeResearchStream(id, {
      onOpen: () => {
        if (cancelled) return;
        setConn("open");
        setReconnectAttempt(0);
        stopPolling();
      },
      onReconnecting: (attempt) => {
        if (cancelled) return;
        setConn("reconnecting");
        setReconnectAttempt(attempt);
        startPolling();
      },
      onGiveUp: () => {
        if (cancelled) return;
        setConn("reconnecting");
        startPolling();
      },
      onQueued: (p) => {
        if (cancelled) return;
        applyProgress(p);
      },
      onProgress: (p) => {
        if (cancelled) return;
        applyProgress(p);
      },
      onCompleted: (p) => {
        if (cancelled) return;
        applyProgress(p);
        stopPolling();
        setConn("closed");
      },
      onFailed: (p, err) => {
        if (cancelled) return;
        applyProgress(p);
        setError(err);
        stopPolling();
        setConn("closed");
      },
    });

    // Initial progress snapshot (fast seed + covers SSE-never-connecting).
    startPolling();
    getJobProgress(id)
      .then((p) => {
        if (cancelled) return;
        applyProgress(p);
      })
      .catch(() => {
        // Ignore — SSE or polling surfaces state.
      });

    return () => {
      cancelled = true;
      stopPolling();
      unsubscribe();
    };
  }, [jobId]);

  return {
    status,
    currentStep,
    completedSteps,
    error,
    connection,
    reconnectAttempt,
    isTerminal: status === "completed" || status === "failed",
  };
}
