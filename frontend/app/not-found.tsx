"use client";

import React from "react";
import AppShell from "@/components/layout/AppShell";
import { Compass, Home } from "lucide-react";
import Link from "next/link";

export default function NotFoundPage() {
  return (
    <AppShell>
      <div className="flex-1 flex items-center justify-center px-6 py-12">
        <div className="max-w-md w-full text-center space-y-5">
          <div className="h-12 w-12 rounded-full bg-muted border border-border flex items-center justify-center text-muted-foreground mx-auto">
            <Compass size={24} />
          </div>
          
          <div className="space-y-2">
            <h2 className="text-base font-bold font-syne text-foreground tracking-tight">
              Resource Not Found (404)
            </h2>
            <p className="text-xs text-muted-foreground leading-relaxed max-w-xs mx-auto">
              The requested address does not exist or has been removed from the research database indexing registry.
            </p>
          </div>

          <div className="pt-2">
            <Link
              href="/"
              className="inline-flex items-center gap-1.5 px-4 py-2 bg-primary text-primary-foreground hover:bg-primary/95 font-semibold text-xs rounded-lg cursor-pointer transition-all shadow-md shadow-primary/10"
            >
              <Home size={13} />
              <span>Return to Workspace</span>
            </Link>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
