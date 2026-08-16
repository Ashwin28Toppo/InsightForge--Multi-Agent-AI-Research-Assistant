"use client";

const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";

export class ApiError extends Error {
  status: number;
  detail: unknown;

  constructor(status: number, detail: unknown) {
    super(typeof detail === "string" ? detail : "API request failed");
    this.status = status;
    this.detail = detail;
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
  };

  const response = await fetch(`${BASE_URL}${endpoint}`, config);
  
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
    throw new ApiError(response.status, errorDetail);
  }

  return response.json() as Promise<T>;
}
