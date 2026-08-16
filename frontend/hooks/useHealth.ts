"use client";

import { useState, useEffect } from "react";
import { getHealth } from "../lib/api/health";

export function useHealth() {
  const [healthStatus, setHealthStatus] = useState<"online" | "offline" | "checking">("checking");

  useEffect(() => {
    async function checkHealth() {
      try {
        const res = await getHealth();
        if (res.status === "ok") {
          setHealthStatus("online");
        } else {
          setHealthStatus("offline");
        }
      } catch {
        setHealthStatus("offline");
      }
    }
    checkHealth();
    
    // Poll health every 30 seconds
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  return { healthStatus };
}
