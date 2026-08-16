"use client";

import React, { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import AppShell from "@/components/layout/AppShell";
import ReportViewer from "@/components/report/ReportViewer";
import TraceabilityRail from "@/components/layout/TraceabilityRail";
import StatusBadge from "@/components/ui/StatusBadge";
import Skeleton from "@/components/feedback/Skeleton";
import EmptyState from "@/components/feedback/EmptyState";
import { ChevronLeft, Calendar, Clock, Database, Compass } from "lucide-react";
import { getHistory, HistoryItem } from "@/lib/history/store";
import { normalizeResearchResult } from "@/lib/utils/normalize";
import type { RailTab } from "@/components/layout/TraceabilityRail";

export default function HistoryDetailPage() {
  const params = useParams();
  const router = useRouter();
  const jobId = (params?.jobId as string) || "";

  const [record, setRecord] = useState<HistoryItem | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [railTab, setRailTab] = useState<RailTab>("citations");
  const [activeCitation, setActiveCitation] = useState<number | null>(null);

  // Resolve the archived record from local history (client-only).
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- client-only localStorage read must happen after hydration
    setRecord(getHistory().find((h) => h.jobId === jobId) ?? null);
    setLoaded(true);
  }, [jobId]);

  const handleCitationRef = (index: number) => {
    setActiveCitation(index);
    setRailTab("citations");
  };

  const result = record?.resultSnapshot
    ? normalizeResearchResult(record.resultSnapshot)
    : null;

  return (
    <AppShell>
      {/* Archive snapshot indicator */}
      <div className="border-b border-border px-6 py-2.5 flex items-center justify-between gap-3 text-xs text-muted-foreground select-none flex-wrap">
        <div className="flex items-center gap-2">
          <Database size={13} className="text-primary" />
          <span className="font-mono text-foreground font-semibold">
            LOCAL SNAPSHOT ARCHIVE
          </span>
          <span className="hidden sm:inline text-muted-foreground">
            Cached locally when the research completed.
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
      ) : !record ? (
        <div className="flex-1 max-w-5xl w-full mx-auto px-6 py-10">
          <EmptyState
            title="Archive record not found"
            body="This snapshot is no longer present in the local index."
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
                  {record.completedAt}
                </span>
                {record.duration && (
                  <span className="inline-flex items-center gap-1.5">
                    <Clock size={13} />
                    Elapsed: {record.duration}
                  </span>
                )}
                <StatusBadge status={record.status} />
                <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded border border-border truncate max-w-[240px]">
                  JOB: {jobId.slice(0, 24)}
                </span>
              </div>

              <h1 className="text-lg md:text-xl font-bold tracking-tight text-foreground leading-relaxed">
                “{record.query}”
              </h1>
            </div>

            {result && result.report ? (
              <ReportViewer
                report={result.report}
                confidence={record.confidence || result.confidence}
                meta={{
                  completedAt: record.completedAt,
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
                  No report snapshot saved
                </p>
                <p className="text-xs text-muted-foreground max-w-md mx-auto">
                  This record was archived without a full report snapshot
                  (e.g. a failed run). Only metadata is available locally.
                </p>
                {record.reportSnippet && (
                  <p className="text-xs text-foreground/80 italic max-w-md mx-auto border-l-2 border-border pl-3 text-left">
                    “{record.reportSnippet}”
                  </p>
                )}
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
    </AppShell>
  );
}
