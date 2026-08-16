"use client";

// NOTE: Real integration will call apiFetch<{ status: string }>("/health") from ./client.

export interface HealthResponse {
  status: string;
}

export async function getHealth(): Promise<HealthResponse> {
  // NOTE: Real integration will call:
  // return apiFetch<HealthResponse>("/health");
  
  return new Promise((resolve) => {
    resolve({ status: "ok" });
  });
}
