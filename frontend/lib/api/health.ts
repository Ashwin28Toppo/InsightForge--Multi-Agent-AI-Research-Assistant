"use client";

import { apiFetch } from "./client";
import type { HealthResponse } from "../types/api";

export function getHealth(signal?: AbortSignal): Promise<HealthResponse> {
  return apiFetch<HealthResponse>("/health", { signal });
}
