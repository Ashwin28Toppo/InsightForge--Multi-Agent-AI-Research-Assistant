"use client";

/** Extract a clean display domain from a URL (e.g. "doi.org"). */
export function getDomain(url?: string | null): string {
  if (!url) return "unknown source";
  try {
    const hostname = new URL(url).hostname;
    return hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}
