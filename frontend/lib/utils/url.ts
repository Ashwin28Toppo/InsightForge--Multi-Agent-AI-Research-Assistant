"use client";

export function getDomain(url?: string | null): string {
  if (!url) return "unknown source";
  try {
    const hostname = new URL(url).hostname;
    return hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}
