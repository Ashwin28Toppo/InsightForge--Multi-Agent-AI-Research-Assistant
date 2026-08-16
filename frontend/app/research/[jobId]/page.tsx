"use client";

import React, { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import AppShell from "@/components/layout/AppShell";
import ProgressTimeline from "@/components/progress/ProgressTimeline";
import ReportViewer from "@/components/report/ReportViewer";
import TraceabilityRail from "@/components/layout/TraceabilityRail";
import StatusBadge from "@/components/ui/StatusBadge";
import { Clock, Info, RefreshCw, Plus } from "lucide-react";
import {
  PIPELINE_STAGES,
  BATTERIES_RESULT,
  runMockResearch,
} from "@/lib/mock/research";
import type { RailTab } from "@/components/layout/TraceabilityRail";

type DemoStatus = "running" | "completed" | "failed";

export default function ResearchWorkspace() {
  const params = useParams();
  const router = useRouter();
  const jobId = (params?.jobId as string) || "unknown";

  const [status, setStatus] = useState<DemoStatus>("running");
  const [currentStep, setCurrentStep] = useState<string | null>("plan");
  const [completedSteps, setCompletedSteps] = useState<string[]>([]);
  const [elapsed, setElapsed] = useState(0);
  const [railTab, setRailTab] = useState<RailTab>("citations");
  const [activeCitation, setActiveCitation] = useState<number | null>(null);

  // Elapsed timer while running
  useEffect(() => {
    if (status !== "running") return;
    const interval = setInterval(() => setElapsed((prev) => prev + 1), 1000);
    return () => clearInterval(interval);
  }, [status]);

  // Start (or restart) the demo run — event-driven, not effect-driven.
  const startRunning = () => {
    setCurrentStep("plan");
    setCompletedSteps([]);
    setElapsed(0);
    setRailTab("citations");
    setStatus("running");
  };

  // Simulate the pipeline running over the dynamic stage list.
  // State updates here happen inside async callbacks (interval + promise),
  // which the react-hooks rules permit.
  useEffect(() => {
    if (status !== "running") return;
    let cancelled = false;
    const completed: string[] = [];

    const run = runMockResearch(
      BATTERIES_RESULT.query || "research",
      (step) => {
        if (cancelled) return;
        setCurrentStep(step);
        completed.push(step);
        setCompletedSteps([...completed]);
      },
      850
    );

    run.then(() => {
      if (!cancelled) setStatus("completed");
    });

    return () => {
      cancelled = true;
    };
  }, [status, jobId]);

  const formatTime = (sec: number) => {
    const mins = Math.floor(sec / 60);
    const secs = sec % 60;
    return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
  };

  const handleCitationRef = (index: number) => {
    setActiveCitation(index);
    setRailTab("citations");
  };

  const retry = startRunning;

  return (
    <AppShell>
      {/* Workspace chrome */}
      <div className="border-b border-border px-6 py-3 flex items-center justify-between gap-4 flex-wrap select-none">
        <div className="flex items-center gap-3 min-w-0">
          <span className="text-[10px] font-mono px-2 py-1 rounded bg-muted border border-border text-muted-foreground truncate">
            JOB: {jobId.slice(0, 24)}
          </span>
          <StatusBadge status={status} />
          <span className="hidden sm:inline-flex items-center gap-1 text-[10px] font-mono text-muted-foreground">
            <Clock size={11} />
            {formatTime(elapsed)}
          </span>
        </div>

        {/* Demo state control (mock phase only) */}
        <div
          className="flex items-center gap-1 p-1 rounded-lg bg-muted border border-border"
          role="group"
          aria-label="Preview research state"
        >
          {(
            [
              { key: "running", label: "Running" },
              { key: "completed", label: "Report" },
              { key: "failed", label: "Failed" },
            ] as { key: DemoStatus; label: string }[]
          ).map((option) => (
            <button
              key={option.key}
              type="button"
              onClick={() =>
                option.key === "running" ? startRunning() : setStatus(option.key)
              }
              className={`px-2.5 py-1 rounded-md text-[10px] font-mono font-bold uppercase tracking-wider cursor-pointer transition-all
                ${status === option.key
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:text-foreground"
                }`}
              aria-pressed={status === option.key}
            >
              {option.label}
            </button>
          ))}
        </div>
      </div>

      {/* Main workspace frame */}
      <div className="flex-1 flex flex-col lg:flex-row overflow-hidden min-h-0">
        {/* Primary column */}
        <div className="flex-1 overflow-y-auto px-6 py-6 space-y-6">
          <div className="space-y-3">
            <h1 className="text-lg md:text-xl font-bold tracking-tight text-foreground leading-relaxed">
              “{BATTERIES_RESULT.query}”
            </h1>
          </div>

          {/* RUNNING */}
          {status === "running" && (
            <div className="space-y-6">
              <ProgressTimeline
                stages={PIPELINE_STAGES}
                currentStep={currentStep}
                completedSteps={completedSteps}
              />
              {/* Report skeleton while pipeline runs */}
              <div
                className="bg-card border border-border rounded-xl p-6 space-y-6 animate-pulse"
                aria-hidden="true"
              >
                <div className="h-6 bg-border rounded-md w-1/3" />
                <div className="space-y-3">
                  <div className="h-4 bg-border rounded-md w-full" />
                  <div className="h-4 bg-border rounded-md w-11/12" />
                  <div className="h-4 bg-border rounded-md w-10/12" />
                </div>
                <div className="space-y-3">
                  <div className="h-4 bg-border rounded-md w-full" />
                  <div className="h-4 bg-border rounded-md w-8/12" />
                </div>
              </div>
            </div>
          )}

          {/* COMPLETED */}
          {status === "completed" && (
            <ReportViewer
              report={BATTERIES_RESULT.report || ""}
              confidence={BATTERIES_RESULT.confidence}
              meta={{
                elapsed: formatTime(elapsed),
                sourceCount: BATTERIES_RESULT.sources?.length,
                citationCount: BATTERIES_RESULT.citations?.length,
                claimCount: BATTERIES_RESULT.claims?.length,
                factCheckCount: BATTERIES_RESULT.fact_checks?.length,
                criticScore: BATTERIES_RESULT.critic_score ?? null,
              }}
              onCitationRef={handleCitationRef}
            />
          )}

          {/* FAILED */}
          {status === "failed" && (
            <div className="bg-card border border-destructive/20 bg-destructive/5 rounded-xl p-8 text-center space-y-4 max-w-xl mx-auto my-12">
              <div className="h-12 w-12 rounded-full bg-destructive/10 border border-destructive/30 flex items-center justify-center text-destructive mx-auto">
                <Info size={24} />
              </div>
              <h2 className="text-base font-bold font-syne text-foreground">
                Research Pipeline Interrupted
              </h2>
              <p className="text-xs text-muted-foreground leading-relaxed max-w-md mx-auto">
                The agent pipeline encountered a rate limit restriction during
                the web research stage (Groq TPM budget exceeded for
                llama-3.1-8b-instant). No partial report was produced.
              </p>
              <div className="pt-2 flex justify-center gap-3">
                <button
                  type="button"
                  onClick={retry}
                  className="flex items-center gap-1.5 px-4 py-2 bg-primary text-primary-foreground font-semibold text-xs rounded-lg hover:bg-primary/95 cursor-pointer shadow-md shadow-primary/10 transition-all"
                >
                  <RefreshCw size={13} />
                  <span>Retry Pipeline</span>
                </button>
                <button
                  type="button"
                  onClick={() => router.push("/")}
                  className="flex items-center gap-1.5 px-4 py-2 border border-border hover:border-border-strong text-muted-foreground hover:text-foreground font-semibold text-xs rounded-lg cursor-pointer transition-all"
                >
                  <Plus size={13} />
                  <span>New Inquiry</span>
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Traceability rail */}
        <TraceabilityRail
          sources={BATTERIES_RESULT.sources}
          evidence={BATTERIES_RESULT.evidence}
          citations={BATTERIES_RESULT.citations}
          factChecks={BATTERIES_RESULT.fact_checks}
          claims={BATTERIES_RESULT.claims}
          activeCitation={activeCitation}
          onSelectCitation={handleCitationRef}
          activeTab={railTab}
          onTabChange={setRailTab}
        />
      </div>
    </AppShell>
  );
}
