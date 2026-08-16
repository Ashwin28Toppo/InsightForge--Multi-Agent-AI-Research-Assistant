"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import AppShell from "@/components/layout/AppShell";
import ResearchComposer from "@/components/research/ResearchComposer";
import { PIPELINE_STAGES, MOCK_HISTORY } from "@/lib/mock/research";
import { ArrowRight, Clock, ShieldCheck } from "lucide-react";

export default function Home() {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(false);

  const handleResearchSubmit = (query: string) => {
    setIsLoading(true);
    // Mock phase: generate a mock job id and navigate to the workspace.
    const tag =
      query.trim().toLowerCase().replace(/\s+/g, "-").slice(0, 24) || "inquiry";
    const mockJobId = `mock-${tag}-${Math.floor(Math.random() * 100000)}`;
    setTimeout(() => {
      router.push(`/research/${mockJobId}`);
    }, 800);
  };

  const recentCompleted = MOCK_HISTORY.filter(
    (item) => item.status === "completed"
  ).slice(0, 3);

  return (
    <AppShell>
      <div className="flex-1 max-w-7xl w-full mx-auto px-6 py-10 space-y-12">
        {/* Hero */}
        <section className="grid grid-cols-1 lg:grid-cols-12 gap-10 items-start">
          <div className="lg:col-span-5 space-y-5 text-left">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-primary/20 bg-primary/5 text-xs font-mono font-semibold text-primary select-none uppercase tracking-widest">
              <ShieldCheck size={13} />
              <span>Evidence-backed pipeline</span>
            </div>

            <h1 className="text-3xl md:text-4xl font-extrabold tracking-tight font-syne text-foreground leading-tight">
              Multi-Agent Research Workstation
            </h1>

            <p className="text-sm md:text-[15px] text-muted-foreground leading-relaxed max-w-md">
              A coordinated pipeline of specialized agents plans, searches the
              web, extracts evidence, fact-checks claims, and drafts a fully
              cited report — with every stage streamed live.
            </p>

            <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-xs text-muted-foreground border-t border-border pt-5 max-w-md">
              <span className="flex items-center gap-2">
                <span className="h-1.5 w-1.5 rounded-full bg-info" aria-hidden="true" />
                Batch fact checking
              </span>
              <span className="flex items-center gap-2">
                <span className="h-1.5 w-1.5 rounded-full bg-info" aria-hidden="true" />
                Deterministic citations
              </span>
              <span className="flex items-center gap-2">
                <span className="h-1.5 w-1.5 rounded-full bg-info" aria-hidden="true" />
                Multi-source extraction
              </span>
              <span className="flex items-center gap-2">
                <span className="h-1.5 w-1.5 rounded-full bg-info" aria-hidden="true" />
                Confidence scoring
              </span>
            </div>
          </div>

          {/* Composer */}
          <div className="lg:col-span-7 space-y-3">
            <h2 className="text-xs font-mono font-bold uppercase tracking-widest text-muted-foreground">
              Initiate Inquiry
            </h2>
            <ResearchComposer onSubmit={handleResearchSubmit} isLoading={isLoading} />
          </div>
        </section>

        {/* Pipeline overview */}
        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xs font-mono font-bold uppercase tracking-widest text-muted-foreground">
              Research Pipeline
            </h2>
            <span className="text-[10px] font-mono text-muted-foreground select-none">
              {PIPELINE_STAGES.length} stages
            </span>
          </div>
          <ol className="grid grid-cols-1 sm:grid-cols-3 lg:grid-cols-9 gap-2">
            {PIPELINE_STAGES.map((stage, idx) => (
              <li
                key={stage.key}
                className="flex items-center gap-2.5 p-3 bg-card border border-border rounded-lg hover:border-border-strong transition-colors"
              >
                <span className="text-[10px] font-mono font-bold text-primary select-none">
                  {String(idx + 1).padStart(2, "0")}
                </span>
                <div className="min-w-0">
                  <p className="text-xs font-semibold text-foreground truncate">
                    {stage.label}
                  </p>
                  <p className="text-[10px] text-muted-foreground truncate">
                    {stage.desc}
                  </p>
                </div>
              </li>
            ))}
          </ol>
        </section>

        {/* Recent research */}
        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xs font-mono font-bold uppercase tracking-widest text-muted-foreground">
              Recent Inquiries
            </h2>
            <button
              type="button"
              onClick={() => router.push("/history")}
              className="inline-flex items-center gap-1 text-[10px] font-mono text-primary hover:underline cursor-pointer"
            >
              View history
              <ArrowRight size={11} />
            </button>
          </div>

          {recentCompleted.length > 0 ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {recentCompleted.map((item) => (
                <div
                  key={item.jobId}
                  onClick={() => router.push(`/research/${item.jobId}`)}
                  className="p-3.5 bg-card hover:bg-muted/30 border border-border hover:border-border-strong rounded-xl cursor-pointer transition-all space-y-2 flex flex-col justify-between group"
                >
                  <p className="text-xs font-semibold text-foreground line-clamp-2 leading-relaxed group-hover:text-primary transition-colors">
                    {item.query}
                  </p>
                  <div className="flex items-center justify-between text-[10px] text-muted-foreground font-mono">
                    <span>{item.date}</span>
                    <span className="inline-flex items-center gap-1">
                      <Clock size={10} />
                      {item.duration}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          ) : null}
        </section>
      </div>
    </AppShell>
  );
}
