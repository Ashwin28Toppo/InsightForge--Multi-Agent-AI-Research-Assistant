"use client";

const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";

export class ApiError extends Error {
  status: number;
  detail: unknown;
  requestId: string | null;

  constructor(status: number, detail: unknown, requestId: string | null = null) {
    super(typeof detail === "string" ? detail : "API request failed");
    this.status = status;
    this.detail = detail;
    this.requestId = requestId;
    this.name = "ApiError";
  }
}

export async function apiFetch<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  // Generate request ID
  const requestId = crypto.randomUUID();
  
  const headers = new Headers(options.headers);
  headers.set("Content-Type", "application/json");
  headers.set("Accept", "application/json");
  headers.set("X-Request-ID", requestId);

  const config: RequestInit = {
    ...options,
    headers,
    // Cookie-based auth (Phase 2F Step 3): the JWT lives in an HttpOnly
    // cookie set by the backend. ``include`` makes the browser attach it on
    // cross-origin calls (localhost:3000 -> 127.0.0.1:8000) and accept the
    // Set-Cookie response. Required to consume the auth/history APIs.
    credentials: "include",
  };

  const response = await fetch(`${BASE_URL}${endpoint}`, config);
  const responseRequestId = response.headers.get("X-Request-ID");

  if (!response.ok) {
    let errorDetail: unknown = "Unknown api connection error";
    try {
      const errJson: unknown = await response.json();
      if (
        typeof errJson === "object" &&
        errJson !== null &&
        "detail" in errJson
      ) {
        errorDetail = (errJson as { detail: unknown }).detail || errorDetail;
      }
    } catch {
      // Non-JSON error body — fall through to the generic message.
    }
    throw new ApiError(response.status, errorDetail, responseRequestId);
  }

  // The health endpoint returns a tiny JSON body; keep responses lenient.
  try {
    return (await response.json()) as T;
  } catch {
    return undefined as T;
  }
}
