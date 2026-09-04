"use client";

import { apiFetch } from "./client";
import type { AuthRequest, UserResponse } from "../types/api";

/**
 * Authentication API client (Phase 2F Steps 3 & 7).
 *
 * The JWT is transported EXCLUSIVELY through the backend's HttpOnly cookie —
 * it is never read, stored, or forwarded by this module. ``credentials:
 * "include"`` (set in ``client.ts``) makes the browser attach the cookie and
 * accept the Set-Cookie response, which is all this code relies on.
 */

export function signup(payload: AuthRequest): Promise<UserResponse> {
  return apiFetch<UserResponse>("/auth/signup", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function login(
  payload: Pick<AuthRequest, "email" | "password">
): Promise<UserResponse> {
  return apiFetch<UserResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getCurrentUser(signal?: AbortSignal): Promise<UserResponse> {
  return apiFetch<UserResponse>("/auth/me", { signal });
}

export function logout(): Promise<void> {
  return apiFetch<void>("/auth/logout", { method: "POST" });
}
