"use client";

import React, { useState, useEffect, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import AppShell from "@/components/layout/AppShell";
import ReportViewer from "@/components/report/ReportViewer";
import TraceabilityRail from "@/components/layout/TraceabilityRail";
import StatusBadge from "@/components/ui/StatusBadge";
import Skeleton from "@/components/feedback/Skeleton";
import EmptyState from "@/components/feedback/EmptyState";
import AuthGate from "@/components/auth/AuthGate";
import { ChevronLeft, Calendar, Clock, Database, Compass, RefreshCw } from "lucide-react";
import { getResearchHistory } from "@/lib/api/research";
import { apiErrorMessage } from "@/lib/utils/errors";
import { normalizeResearchResult } from "@/lib/utils/normalize";
import type { ResearchHistoryItem } from "@/lib/types/api";
import type { RailTab } from "@/components/layout/TraceabilityRail";

/** Format an ISO timestamp defensively for display. */
function formatDateTime(iso: string | undefined): string {
  if (!iso) return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/** Server-backed detail (rendered only when authenticated). */
function HistoryDetailContent({ jobId }: { jobId: string }) {
  const router = useRouter();
  const [record, setRecord] = useState<ResearchHistoryItem | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [railTab, setRailTab] = useState<RailTab>("citations");
  const [activeCitation, setActiveCitation] = useState<number | null>(null);

  // Resolve the record from the authenticated user's server-side history.
  const load = useCallback(async () => {
    setLoaded(false);
    setLoadError(null);
    try {
      const res = await getResearchHistory();
      setRecord(res.jobs.find((j) => j.job_id === jobId) ?? null);
    } catch (err) {
      setLoadError(apiErrorMessage(err));
    } finally {
      setLoaded(true);
    }
  }, [jobId]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- fetch must reset loading state; same pattern as the rest of the app
    void load();
  }, [load]);

  const handleCitationRef = (index: number) => {
    setActiveCitation(index);
    setRailTab("citations");
  };

  const result = record?.result
    ? normalizeResearchResult(record.result)
    : null;

  return (
    <>
      {/* Archive indicator */}
      <div className="border-b border-border px-6 py-2.5 flex items-center justify-between gap-3 text-xs text-muted-foreground select-none flex-wrap">
        <div className="flex items-center gap-2">
          <Database size={13} className="text-primary" />
          <span className="font-mono text-foreground font-semibold">
            SERVER ARCHIVE
          </span>
          <span className="hidden sm:inline text-muted-foreground">
            Stored on the backend, scoped to your account.
          </span>
        </div>
        <button
          type="button"
          onClick={() => router.push("/history")}
          className="flex items-center gap-1 hover:text-foreground underline cursor-pointer"
        >
          <span>Back to archives</span>
        </button>
      </div>

      {!loaded ? (
        <div className="flex-1 max-w-5xl w-full mx-auto px-6 py-10 space-y-6">
          <div className="bg-card border border-border rounded-xl p-6">
            <Skeleton lines={4} />
          </div>
        </div>
      ) : loadError ? (
        <div className="flex-1 max-w-5xl w-full mx-auto px-6 py-10">
          <div className="bg-card border border-destructive/25 rounded-xl p-8 text-center space-y-4">
            <p className="text-sm font-semibold text-foreground">
              Could not load this archive record
            </p>
            <p className="text-xs text-muted-foreground max-w-md mx-auto leading-relaxed">
              {loadError}
            </p>
            <button
              type="button"
              onClick={() => void load()}
              className="inline-flex items-center gap-1.5 px-4 py-2 bg-primary text-primary-foreground font-semibold text-xs rounded-lg hover:bg-primary/95 cursor-pointer transition-all"
            >
              <RefreshCw size={13} />
              <span>Retry</span>
            </button>
          </div>
        </div>
      ) : !record ? (
        <div className="flex-1 max-w-5xl w-full mx-auto px-6 py-10">
          <EmptyState
            title="Archive record not found"
            body="This record is no longer present in your history (it may have expired)."
            icon={<Compass size={18} />}
            action={
              <button
                type="button"
                onClick={() => router.push("/history")}
                className="inline-flex px-4 py-2 bg-primary text-primary-foreground font-semibold text-xs rounded-lg cursor-pointer transition-all"
              >
                Back to history
              </button>
            }
          />
        </div>
      ) : (
        <div className="flex-1 flex flex-col lg:flex-row overflow-hidden min-h-0">
          {/* Primary column */}
          <div className="flex-1 overflow-y-auto px-6 py-6 space-y-6">
            <div className="space-y-4">
              <button
                type="button"
                onClick={() => router.push("/history")}
                className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground cursor-pointer transition-all"
              >
                <ChevronLeft size={16} />
                <span>Back to history</span>
              </button>

              <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground font-mono">
                <span className="inline-flex items-center gap-1.5">
                  <Calendar size={13} />
                  Created: {formatDateTime(record.created_at)}
                </span>
                <span className="inline-flex items-center gap-1.5">
                  <Clock size={13} />
                  Updated: {formatDateTime(record.updated_at)}
                </span>
                <StatusBadge status={record.status} />
                <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded border border-border truncate max-w-[240px]">
                  JOB: {jobId.slice(0, 24)}
                </span>
              </div>

              {(record.current_step || (record.completed_steps?.length ?? 0) > 0) && (
                <div className="flex items-center gap-1.5 flex-wrap text-[10px] font-mono text-muted-foreground">
                  {record.current_step && (
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-muted border border-border">
                      <Clock size={10} />
                      STEP: {record.current_step}
                    </span>
                  )}
                  {(record.completed_steps?.length ?? 0) > 0 && (
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-muted border border-border">
                      {record.completed_steps!.length} stage
                      {record.completed_steps!.length === 1 ? "" : "s"}
                    </span>
                  )}
                </div>
              )}

              <h1 className="text-lg md:text-xl font-bold tracking-tight text-foreground leading-relaxed">
                “{record.query}”
              </h1>
            </div>

            {record.status === "failed" && record.error ? (
              <div className="bg-card border border-destructive/25 rounded-xl p-8 text-center space-y-3">
                <p className="text-sm font-semibold text-foreground">
                  This research run failed
                </p>
                <p className="text-xs text-destructive max-w-md mx-auto leading-relaxed">
                  {record.error}
                </p>
              </div>
            ) : result && result.report ? (
              <ReportViewer
                report={result.report}
                confidence={result.confidence}
                meta={{
                  completedAt: formatDateTime(record.updated_at),
                  sourceCount: result.sources?.length,
                  citationCount: result.citations?.length,
                  claimCount: result.claims?.length,
                  factCheckCount: result.fact_checks?.length,
                  criticScore: result.critic_score ?? null,
                }}
                onCitationRef={handleCitationRef}
              />
            ) : (
              <div className="bg-card border border-border rounded-xl p-8 text-center space-y-3">
                <p className="text-sm font-semibold text-foreground">
                  No report available
                </p>
                <p className="text-xs text-muted-foreground max-w-md mx-auto">
                  This record has no full report payload yet (e.g. it is still
                  running or the result is unavailable).
                </p>
              </div>
            )}
          </div>

          {/* Traceability rail (only when a snapshot exists) */}
          {result ? (
            <TraceabilityRail
              sources={result.sources}
              evidence={result.evidence}
              citations={result.citations}
              factChecks={result.fact_checks}
              claims={result.claims}
              activeCitation={activeCitation}
              onSelectCitation={handleCitationRef}
              activeTab={railTab}
              onTabChange={setRailTab}
            />
          ) : null}
        </div>
      )}
    </>
  );
}

export default function HistoryDetailPage() {
  const params = useParams();
  const jobId = (params?.jobId as string) || "";

  return (
    <AppShell>
      <AuthGate
        promptTitle="Sign in to view this archive"
        promptBody="Research history is stored per user on the server. Sign in to view this record."
      >
        <HistoryDetailContent jobId={jobId} />
      </AuthGate>
    </AppShell>
  );
}
