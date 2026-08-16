"use client";

import React, { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import AppShell from "@/components/layout/AppShell";
import ResearchComposer from "@/components/research/ResearchComposer";
import { submitResearch } from "@/lib/api/research";
import { apiErrorMessage } from "@/lib/utils/errors";
import { getHistory } from "@/lib/history/store";
import { PIPELINE_STAGES } from "@/lib/mock/research";
import { ArrowRight, Clock } from "lucide-react";
import ConfidenceBadge from "@/components/ui/ConfidenceBadge";

interface RecentItem {
  jobId: string;
  query: string;
  date: string;
  duration?: string;
  confidence?: string;
}

export default function Home() {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [recent, setRecent] = useState<RecentItem[]>([]);
  const submittingRef = useRef(false);

  // Load recent completed research from the local history store (client-only).
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- client-only localStorage read must happen after hydration
    setRecent(
      getHistory()
        .filter((h) => h.status === "completed")
        .slice(0, 3)
        .map((h) => ({
          jobId: h.jobId,
          query: h.query,
          date: h.completedAt,
          duration: h.duration,
          confidence: h.confidence,
        }))
    );
  }, []);

  const handleResearchSubmit = async (query: string) => {
    // Prevent accidental duplicate submissions (backend has no idempotency key).
    if (submittingRef.current) return;
    submittingRef.current = true;
    setIsLoading(true);
    setSubmitError(null);
    try {
      const res = await submitResearch(query);
      sessionStorage.setItem("insightforge-last-query", query);
      router.push(`/research/${res.job_id}`);
    } catch (err) {
      setSubmitError(apiErrorMessage(err));
      setIsLoading(false);
      submittingRef.current = false;
    }
  };

  return (
    <AppShell>
      <div className="flex-1 max-w-5xl w-full mx-auto px-6 py-10 space-y-12">
        {/* Header — restrained workstation intro, not a landing hero */}
        <section className="space-y-2">
          <p className="text-xs font-mono font-bold uppercase tracking-widest text-primary select-none">
            Research Workstation
          </p>
          <h1 className="text-2xl md:text-3xl font-bold font-syne tracking-tight text-foreground">
            Start an investigation
          </h1>
          <p className="text-sm text-muted-foreground leading-relaxed max-w-2xl">
            Submit a query and a coordinated pipeline of agents will plan,
            search the web, extract evidence, fact-check claims, and draft a
            fully cited report — streamed live as it runs.
          </p>
        </section>

        {/* Composer — the primary action */}
        <section className="space-y-3 max-w-3xl">
          <h2 className="text-xs font-mono font-bold uppercase tracking-widest text-muted-foreground">
            Research Query
          </h2>
          <ResearchComposer
            onSubmit={handleResearchSubmit}
            isLoading={isLoading}
            externalError={submitError}
          />
        </section>

        {/* Pipeline overview — compact execution trace */}
        <section className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-xs font-mono font-bold uppercase tracking-widest text-muted-foreground">
              Pipeline
            </h2>
            <span className="text-[10px] font-mono text-muted-foreground select-none">
              {PIPELINE_STAGES.length} stages
            </span>
          </div>
          <div className="bg-card border border-border rounded-xl overflow-hidden">
            <ol className="grid grid-cols-1 sm:grid-cols-3 lg:grid-cols-9 divide-y sm:divide-y-0 sm:divide-x divide-border">
              {PIPELINE_STAGES.map((stage, idx) => (
                <li
                  key={stage.key}
                  className="flex items-start gap-2.5 p-3 min-w-0"
                >
                  <span className="text-[10px] font-mono font-bold text-primary mt-0.5 select-none">
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
          </div>
        </section>

        {/* Recent research (from local history) */}
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

          {recent.length > 0 ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {recent.map((item) => (
                <div
                  key={item.jobId}
                  onClick={() => router.push(`/research/${item.jobId}`)}
                  className="p-4 bg-card hover:bg-muted/30 border border-border hover:border-border-strong rounded-xl cursor-pointer transition-all space-y-2.5 flex flex-col justify-between group"
                >
                  <p className="text-xs font-semibold text-foreground line-clamp-2 leading-relaxed group-hover:text-primary transition-colors">
                    {item.query}
                  </p>
                  <div className="flex items-center justify-between gap-2 text-[10px] text-muted-foreground font-mono">
                    <span className="truncate">{item.date}</span>
                    <span className="inline-flex items-center gap-1 shrink-0">
                      <Clock size={11} />
                      {item.duration || "—"}
                    </span>
                  </div>
                  {item.confidence && (
                    <div className="flex justify-end">
                      <ConfidenceBadge confidence={item.confidence} />
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div className="bg-card border border-border border-dashed rounded-xl py-8 px-6 text-center">
              <p className="text-xs text-muted-foreground">
                No research yet — completed runs will be archived here.
              </p>
            </div>
          )}
        </section>
      </div>
    </AppShell>
  );
}
