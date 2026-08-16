"use client";

import React, { useEffect } from "react";
import AppShell from "@/components/layout/AppShell";
import { AlertCircle, RefreshCw, Home } from "lucide-react";
import Link from "next/link";

interface ErrorProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function ErrorPage({ error, reset }: ErrorProps) {
  useEffect(() => {
    // Log error to console/observability service
    console.error("Unhandled runtime boundary error:", error);
  }, [error]);

  return (
    <AppShell healthStatus="offline">
      <div className="flex-1 flex items-center justify-center px-6 py-12">
        <div className="max-w-md w-full bg-card border border-destructive/20 bg-destructive/5 rounded-xl p-8 text-center space-y-5">
          <div className="h-12 w-12 rounded-full bg-destructive/10 border border-destructive/25 flex items-center justify-center text-destructive mx-auto">
            <AlertCircle size={24} />
          </div>
          
          <div className="space-y-2">
            <h2 className="text-base font-bold font-syne text-foreground">
              Application Runtime Interruption
            </h2>
            <p className="text-xs text-muted-foreground leading-relaxed">
              An unexpected failure has interrupted the interface workspace. Review the diagnostic digest below.
            </p>
          </div>

          <div className="p-3 bg-background rounded-lg border border-border text-left font-mono text-[10px] text-muted-foreground overflow-x-auto">
            <p className="font-semibold text-foreground">Error Digest:</p>
            <p className="mt-1">{error.message || "Unknown runtime boundary failure"}</p>
            {error.digest && <p className="mt-0.5">Digest: {error.digest}</p>}
          </div>

          <div className="pt-2 flex justify-center gap-3">
            <button
              onClick={() => reset()}
              className="flex items-center gap-1.5 px-4 py-2 bg-primary text-primary-foreground font-semibold text-xs rounded-lg hover:bg-primary/95 cursor-pointer shadow-md shadow-primary/10 transition-all"
            >
              <RefreshCw size={13} />
              <span>Retry Session</span>
            </button>
            <Link
              href="/"
              className="flex items-center gap-1.5 px-4 py-2 border border-border hover:border-border-strong text-muted-foreground hover:text-foreground font-semibold text-xs rounded-lg cursor-pointer transition-all"
            >
              <Home size={13} />
              <span>Return Home</span>
            </Link>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
