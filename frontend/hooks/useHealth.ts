"use client";

import { useState, useEffect } from "react";
import { getHealth } from "../lib/api/health";

export function useHealth() {
  const [healthStatus, setHealthStatus] = useState<
    "online" | "offline" | "checking"
  >("checking");

  useEffect(() => {
    let cancelled = false;
    const controller = new AbortController();

    async function checkHealth() {
      try {
        const res = await getHealth(controller.signal);
        if (cancelled) return;
        setHealthStatus(res.status === "ok" ? "online" : "offline");
      } catch {
        // Aborted by unmount, or backend unreachable — only update if alive.
        if (!cancelled) setHealthStatus("offline");
      }
    }

    checkHealth();
    // Poll health every 30 seconds.
    const interval = setInterval(() => {
      if (!cancelled) checkHealth();
    }, 30000);

    return () => {
      cancelled = true;
      controller.abort();
      clearInterval(interval);
    };
  }, []);

  return { healthStatus };
}
