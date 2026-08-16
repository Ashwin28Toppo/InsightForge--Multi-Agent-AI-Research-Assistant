"use client";

import type { SseProgressPayload, SseFailedPayload } from "../types/api";

export interface StreamHandlers {
  onOpen?: () => void;
  onQueued?: (payload: SseProgressPayload) => void;
  onProgress?: (payload: SseProgressPayload) => void;
  onCompleted?: (payload: SseProgressPayload) => void;
  onFailed?: (payload: SseFailedPayload, error: string) => void;
  onReconnecting?: (attempt: number) => void;
  /** Reconnection gave up (max attempts reached); caller may fall back to polling. */
  onGiveUp?: () => void;
  /** Terminal event received; the stream is closed. */
  onTerminal?: () => void;
}

const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";
const INITIAL_RETRY_MS = 1000;
const MAX_RETRY_MS = 15000;
const MAX_RETRY_ATTEMPTS = 6;

/** Parse an SSE data payload defensively — never throw on malformed JSON. */
function parsePayload(data: string): SseProgressPayload | null {
  try {
    const parsed: unknown = JSON.parse(data);
    if (
      parsed &&
      typeof parsed === "object" &&
      typeof (parsed as Record<string, unknown>).status === "string"
    ) {
      return parsed as SseProgressPayload;
    }
    return null;
  } catch {
    return null;
  }
}

/**
 * Subscribe to the job's Server-Sent Events stream.
 *
 * - Reconnects with exponential backoff (capped) when the connection drops
 *   while the job is still active.
 * - NEVER creates a new research job — it only reconnects to the same
 *   `/research/{jobId}/stream` endpoint.
 * - Stops reconnecting after a terminal (completed/failed) event.
 * - Returns a cleanup function that closes the stream and cancels timers.
 */
export function subscribeResearchStream(
  jobId: string,
  handlers: StreamHandlers
): () => void {
  if (typeof window === "undefined") {
    return () => {};
  }

  let source: EventSource | null = null;
  let closed = false;
  let terminal = false;
  let retryAttempt = 0;
  let retryTimer: ReturnType<typeof setTimeout> | null = null;

  const url = `${BASE_URL}/research/${encodeURIComponent(jobId)}/stream`;

  const scheduleReconnect = () => {
    if (closed || terminal) return;
    if (retryAttempt >= MAX_RETRY_ATTEMPTS) {
      handlers.onGiveUp?.();
      return;
    }
    const delay = Math.min(INITIAL_RETRY_MS * 2 ** retryAttempt, MAX_RETRY_MS);
    retryAttempt += 1;
    handlers.onReconnecting?.(retryAttempt);
    retryTimer = setTimeout(() => {
      retryTimer = null;
      connect();
    }, delay);
  };

  const connect = () => {
    if (closed || terminal) return;
    // Phase 2F Step 7: the stream endpoint is authenticated — EventSource
    // does NOT send cookies cross-origin unless explicitly enabled.
    const es = new EventSource(url, { withCredentials: true });
    source = es;

    es.addEventListener("open", () => {
      if (closed || terminal) return;
      retryAttempt = 0;
      handlers.onOpen?.();
    });

    es.addEventListener("queued", (event) => {
      if (closed) return;
      const payload = parsePayload((event as MessageEvent).data);
      if (payload) handlers.onQueued?.(payload);
    });

    es.addEventListener("progress", (event) => {
      if (closed) return;
      const payload = parsePayload((event as MessageEvent).data);
      if (payload) handlers.onProgress?.(payload);
    });

    es.addEventListener("completed", (event) => {
      if (closed) return;
      const payload = parsePayload((event as MessageEvent).data);
      terminal = true;
      es.close();
      if (payload) handlers.onCompleted?.(payload);
      handlers.onTerminal?.();
    });

    es.addEventListener("failed", (event) => {
      if (closed) return;
      const payload = parsePayload((event as MessageEvent).data);
      const failed: SseFailedPayload = payload
        ? { ...payload, error: payload.error || "Research job failed" }
        : {
            job_id: jobId,
            status: "failed",
            current_step: null,
            completed_steps: [],
            error: "Research job failed",
          };
      terminal = true;
      es.close();
      handlers.onFailed?.(failed, failed.error);
      handlers.onTerminal?.();
    });

    es.onerror = () => {
      // Fired on network drops AND after es.close(); only reconnect while
      // the job is still active and we didn't close deliberately.
      if (terminal || closed) return;
      es.close();
      scheduleReconnect();
    };
  };

  connect();

  return () => {
    closed = true;
    if (retryTimer) {
      clearTimeout(retryTimer);
      retryTimer = null;
    }
    if (source) {
      source.close();
      source = null;
    }
  };
}
