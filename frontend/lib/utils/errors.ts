"use client";

import { ApiError } from "../api/client";

/**
 * Map API/network failures to clean, user-facing messages.
 * Never exposes stack traces, internal paths, or backend internals.
 */
export function apiErrorMessage(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.status === 404) {
      return "Research job not found or expired.";
    }
    if (err.status === 422) {
      return "The research query was rejected — please check it isn't empty.";
    }
    if (err.status === 500) {
      const ref = err.requestId ? ` (ref ${err.requestId.slice(0, 8)})` : "";
      return `The research service hit an internal error${ref}. Please try again.`;
    }
    return `The research service returned an error (${err.status}). Please try again.`;
  }
  if (err instanceof TypeError) {
    // fetch() throws TypeError on network failure.
    return "Could not reach the research service. Make sure the backend is running.";
  }
  if (err instanceof Error && err.message) {
    return err.message;
  }
  return "Something went wrong. Please try again.";
}
