"use client";

import React, { useState, useEffect, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import AppShell from "@/components/layout/AppShell";
import ProgressTimeline, { ProgressStage } from "@/components/progress/ProgressTimeline";
import ReportViewer from "@/components/report/ReportViewer";
import TraceabilityRail from "@/components/layout/TraceabilityRail";
import StatusBadge from "@/components/ui/StatusBadge";
import Skeleton from "@/components/feedback/Skeleton";
import { useResearchStream } from "@/hooks/useResearchStream";
import { useResearchJob } from "@/hooks/useResearchJob";
import { submitResearch } from "@/lib/api/research";
import { apiErrorMessage } from "@/lib/utils/errors";
import { saveHistoryItem } from "@/lib/history/store";
import { PIPELINE_STAGES } from "@/lib/mock/research";
import {
  Clock,
  Info,
  RefreshCw,
  Plus,
  Radio,
  Wifi,
  WifiOff,
} from "lucide-react";
import type { RailTab } from "@/components/layout/TraceabilityRail";

const formatTime = (sec: number) => {
  const mins = Math.floor(sec / 60);
  const secs = sec % 60;
  return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
};

const getLastQuery = () => {
  if (typeof window === "undefined") return "";
  return sessionStorage.getItem("insightforge-last-query") || "";
};

export default function ResearchWorkspace() {
  const params = useParams();
  const router = useRouter();
  const jobId = (params?.jobId as string) || "";

  // Gate the stream off once the job is known to be missing/expired so the
  // SSE + progress fallback stop (no pointless reconnects or polling).
  const job = useResearchJob(jobId || null);
  const stream = useResearchStream(job.notFound ? null : jobId || null);

  const [railTab, setRailTab] = useState<RailTab>("citations");
  const [activeCitation, setActiveCitation] = useState<number | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const [retryError, setRetryError] = useState<string | null>(null);
  const [retrying, setRetrying] = useState(false);

  const startRef = useRef<number | null>(null);
  const terminalHandledRef = useRef(false);
  const savedRef = useRef(false);
  const [lastQuery, setLastQuery] = useState<string>("");

  // Read the submitted query from sessionStorage post-hydration (client-only
  // value must not be read during render — that would cause a hydration
  // mismatch).
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- client-only sessionStorage read must happen after hydration
    setLastQuery(getLastQuery());
  }, []);

  const status = job.notFound ? "failed" : stream.status;

  // Elapsed timer while the job is active.
  useEffect(() => {
    if (job.notFound) return;
    const active = stream.status === "queued" || stream.status === "running";
    if (!active) return;
    if (startRef.current === null) startRef.current = Date.now();
    const interval = setInterval(() => {
      if (startRef.current !== null) {
        setElapsed(Math.floor((Date.now() - startRef.current) / 1000));
      }
    }, 1000);
    return () => clearInterval(interval);
  }, [stream.status, job.notFound]);

  // On a terminal SSE event, hydrate the final result / authoritative error.
  useEffect(() => {
    if (stream.isTerminal && !terminalHandledRef.current) {
      terminalHandledRef.current = true;
      // Defer to a microtask so no setState runs synchronously in the effect.
      void Promise.resolve().then(() => job.refresh());
    }
  }, [stream.isTerminal, job]);

  // Save a local snapshot once a completed result is available.
  useEffect(() => {
    if (!job.result || stream.status !== "completed" || savedRef.current) {
      return;
    }
    savedRef.current = true;
    saveHistoryItem({
      jobId,
      query: job.result.query || lastQuery || "Research inquiry",
      status: "completed",
      confidence: job.result.confidence,
      reportSnippet: job.result.report ? job.result.report.slice(0, 240) : undefined,
      duration: formatTime(elapsed),
      resultSnapshot: job.result,
    });
  }, [job.result, stream.status, jobId, elapsed, lastQuery]);

  const handleCitationRef = (index: number) => {
    setActiveCitation(index);
    setRailTab("citations");
  };

  // Retry creates a NEW research job only when the user explicitly asks.
  const retry = async () => {
    if (retrying) return;
    const query = lastQuery || job.result?.query || "";
    if (!query) {
      setRetryError("No query is available to retry — start a new inquiry.");
      return;
    }
    setRetrying(true);
    setRetryError(null);
    try {
      const res = await submitResearch(query);
      sessionStorage.setItem("insightforge-last-query", query);
      router.push(`/research/${res.job_id}`);
    } catch (err) {
      setRetryError(apiErrorMessage(err));
      setRetrying(false);
    }
  };

  // Timeline stages: the known pipeline plus any extra keys the backend may
  // surface (loop repeats are handled positionally by completedSteps length).
  const knownKeys = new Set(PIPELINE_STAGES.map((s) => s.key));
  const extraStages: ProgressStage[] = stream.completedSteps
    .filter((key) => !knownKeys.has(key))
    .map((key) => ({ key, label: key }));
  const stages: ProgressStage[] = [...PIPELINE_STAGES, ...extraStages];

  const connectionLabel =
    stream.connection === "open"
      ? "Live stream"
      : stream.connection === "reconnecting"
        ? `Reconnecting… (${stream.reconnectAttempt})`
        : stream.connection === "closed"
          ? "Stream closed"
          : "Connecting…";

  return (
    <AppShell>
      {/* Workspace chrome */}
      <div className="border-b border-border px-6 py-3 flex items-center justify-between gap-4 flex-wrap select-none">
        <div className="flex items-center gap-3 min-w-0">
          <span className="text-[10px] font-mono px-2 py-1 rounded bg-muted border border-border text-muted-foreground truncate">
            JOB: {jobId.slice(0, 24)}
          </span>
          <StatusBadge status={status} />
          {(stream.status === "queued" || stream.status === "running") && (
            <span className="hidden sm:inline-flex items-center gap-1 text-[10px] font-mono text-muted-foreground">
              <Clock size={11} />
              {formatTime(elapsed)}
            </span>
          )}
        </div>

        {!job.notFound && (
        <span
          className={`inline-flex items-center gap-1.5 text-[10px] font-mono uppercase tracking-wider select-none
            ${stream.connection === "open" ? "text-success" : stream.connection === "reconnecting" ? "text-warning" : "text-muted-foreground"}`}
          title="SSE connection state"
        >
          {stream.connection === "open" ? (
            <Wifi size={11} />
          ) : stream.connection === "reconnecting" ? (
            <Radio size={11} />
          ) : (
            <WifiOff size={11} />
          )}
          {connectionLabel}
        </span>
        )}
      </div>

      {/* Not found / expired */}
      {job.notFound ? (
        <div className="flex-1 flex items-center justify-center px-6 py-12">
          <div className="max-w-md w-full bg-card border border-border rounded-xl p-8 text-center space-y-4">
            <div className="h-12 w-12 rounded-full bg-muted border border-border flex items-center justify-center text-muted-foreground mx-auto">
              <Info size={24} />
            </div>
            <h2 className="text-base font-bold font-syne text-foreground">
              Research job not found
            </h2>
            <p className="text-xs text-muted-foreground leading-relaxed">
              This job does not exist or has expired (terminal jobs are cleaned
              up after a short retention window). Start a new inquiry.
            </p>
            <div className="pt-2 flex justify-center gap-3">
              <button
                type="button"
                onClick={() => router.push("/")}
                className="flex items-center gap-1.5 px-4 py-2 bg-primary text-primary-foreground font-semibold text-xs rounded-lg hover:bg-primary/95 cursor-pointer transition-all"
              >
                <Plus size={13} />
                <span>New Inquiry</span>
              </button>
            </div>
          </div>
        </div>
      ) : (
        <div className="flex-1 flex flex-col lg:flex-row overflow-hidden min-h-0">
          {/* Primary column */}
          <div className="flex-1 overflow-y-auto px-6 py-6 space-y-6">
            <div className="space-y-3">
              <h1 className="text-lg md:text-xl font-bold tracking-tight text-foreground leading-relaxed">
                “{job.result?.query || lastQuery || "Research inquiry"}”
              </h1>
            </div>

            {/* QUEUED / RUNNING */}
            {(stream.status === "queued" || stream.status === "running") && (
              <div className="space-y-6">
                <ProgressTimeline
                  stages={stages}
                  currentStep={stream.currentStep}
                  completedSteps={stream.completedSteps}
                />
                {stream.status === "queued" && (
                  <p className="text-xs text-muted-foreground">
                    Job queued — the research worker is starting.
                  </p>
                )}
                {/* Report skeleton while the pipeline runs */}
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
            {stream.status === "completed" &&
              (job.result && job.result.report ? (
                <ReportViewer
                  report={job.result.report}
                  confidence={job.result.confidence}
                  meta={{
                    elapsed: formatTime(elapsed),
                    sourceCount: job.result.sources?.length,
                    citationCount: job.result.citations?.length,
                    claimCount: job.result.claims?.length,
                    factCheckCount: job.result.fact_checks?.length,
                    criticScore: job.result.critic_score ?? null,
                  }}
                  onCitationRef={handleCitationRef}
                />
              ) : job.loading ? (
                <div className="bg-card border border-border rounded-xl p-6 space-y-6">
                  <Skeleton lines={4} />
                </div>
              ) : (
                <div className="bg-card border border-border rounded-xl p-8 text-center space-y-3">
                  <p className="text-sm font-semibold text-foreground">
                    Research completed
                  </p>
                  <p className="text-xs text-muted-foreground max-w-md mx-auto">
                    The pipeline finished but returned no report content.
                  </p>
                </div>
              ))}

            {/* FAILED */}
            {stream.status === "failed" && (
              <div className="bg-card border border-destructive/20 bg-destructive/5 rounded-xl p-8 text-center space-y-4 max-w-xl mx-auto my-12">
                <div className="h-12 w-12 rounded-full bg-destructive/10 border border-destructive/30 flex items-center justify-center text-destructive mx-auto">
                  <Info size={24} />
                </div>
                <h2 className="text-base font-bold font-syne text-foreground">
                  Research Pipeline Failed
                </h2>
                <p className="text-xs text-muted-foreground leading-relaxed max-w-md mx-auto">
                  {stream.error || job.error || "The research job failed."}
                </p>
                {retryError && (
                  <p className="text-xs text-destructive">{retryError}</p>
                )}
                <div className="pt-2 flex justify-center gap-3">
                  <button
                    type="button"
                    onClick={retry}
                    disabled={retrying}
                    className="flex items-center gap-1.5 px-4 py-2 bg-primary text-primary-foreground font-semibold text-xs rounded-lg hover:bg-primary/95 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                  >
                    <RefreshCw size={13} className={retrying ? "animate-spin" : ""} />
                    <span>{retrying ? "Submitting…" : "Retry Pipeline"}</span>
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
            sources={job.result?.sources}
            evidence={job.result?.evidence}
            citations={job.result?.citations}
            factChecks={job.result?.fact_checks}
            claims={job.result?.claims}
            activeCitation={activeCitation}
            onSelectCitation={handleCitationRef}
            activeTab={railTab}
            onTabChange={setRailTab}
          />
        </div>
      )}
    </AppShell>
  );
}
