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

/** Register a new user; the backend sets the access cookie on success. */
export function signup(payload: AuthRequest): Promise<UserResponse> {
  return apiFetch<UserResponse>("/auth/signup", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

/** Log in; the backend sets the access cookie on success. */
export function login(
  payload: Pick<AuthRequest, "email" | "password">
): Promise<UserResponse> {
  return apiFetch<UserResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

/** Resolve the current session (401 when there is no valid cookie). */
export function getCurrentUser(signal?: AbortSignal): Promise<UserResponse> {
  return apiFetch<UserResponse>("/auth/me", { signal });
}

/** Clear the session cookie (idempotent — safe when already signed out). */
export function logout(): Promise<void> {
  return apiFetch<void>("/auth/logout", { method: "POST" });
}
