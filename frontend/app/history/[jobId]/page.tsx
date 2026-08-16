"use client";

import React, { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import AppShell from "@/components/layout/AppShell";
import ReportViewer from "@/components/report/ReportViewer";
import TraceabilityRail from "@/components/layout/TraceabilityRail";
import Skeleton from "@/components/feedback/Skeleton";
import { ChevronLeft, Calendar, Clock, Database } from "lucide-react";
import { getHistory } from "@/lib/history/store";
import {
  MOCK_HISTORY,
  REASONING_RESULT,
  resultForTopic,
} from "@/lib/mock/research";
import type { ResearchResult } from "@/lib/types/api";
import type { RailTab } from "@/components/layout/TraceabilityRail";

interface SnapshotView {
  query: string;
  date: string;
  duration: string;
  result: ResearchResult;
  confidence: string;
}

export default function HistoryDetailPage() {
  const params = useParams();
  const router = useRouter();
  const jobId = (params?.jobId as string) || "unknown";

  const [snapshot, setSnapshot] = useState<SnapshotView | null>(null);
  const [railTab, setRailTab] = useState<RailTab>("citations");
  const [activeCitation, setActiveCitation] = useState<number | null>(null);

  // Resolve the record from local history (client-only) post-hydration;
  // fall back to mock for the demo.
  useEffect(() => {
    const record = getHistory().find((h) => h.jobId === jobId);
    const mockRecord = MOCK_HISTORY.find((m) => m.jobId === jobId);

    if (record) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- client-only localStorage read must happen after hydration
      setSnapshot({
        query: record.query,
        date: record.completedAt,
        duration: record.duration || "—",
        confidence: record.confidence || "unknown",
        result:
          record.resultSnapshot ?? resultForTopic(mockRecord?.topic ?? "reasoning"),
      });
    } else {
      // Unknown archive id → show the reasoning demo record.
      setSnapshot({
        query: REASONING_RESULT.query || "Reasoning methods in frontier LLMs",
        date: mockRecord?.date ?? "August 15, 2026",
        duration: mockRecord?.duration ?? "02:45",
        confidence: REASONING_RESULT.confidence || "medium",
        result: REASONING_RESULT,
      });
    }
  }, [jobId]);

  const handleCitationRef = (index: number) => {
    setActiveCitation(index);
    setRailTab("citations");
  };

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
            Cached report snapshot — the original job may have expired on the
            server.
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

      {snapshot === null ? (
        <div className="flex-1 max-w-5xl w-full mx-auto px-6 py-10 space-y-6">
          <div className="bg-card border border-border rounded-xl p-6">
            <Skeleton lines={4} />
          </div>
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

              <div className="flex flex-wrap items-center gap-4 text-xs text-muted-foreground font-mono">
                <span className="inline-flex items-center gap-1.5">
                  <Calendar size={13} />
                  {snapshot.date}
                </span>
                <span className="inline-flex items-center gap-1.5">
                  <Clock size={13} />
                  Elapsed: {snapshot.duration}
                </span>
                <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded border border-border truncate max-w-[240px]">
                  JOB: {jobId.slice(0, 24)}
                </span>
              </div>

              <h1 className="text-lg md:text-xl font-bold tracking-tight text-foreground leading-relaxed">
                “{snapshot.query}”
              </h1>
            </div>

            <ReportViewer
              report={snapshot.result.report || ""}
              confidence={snapshot.confidence}
              meta={{
                completedAt: snapshot.date,
                sourceCount: snapshot.result.sources?.length,
                citationCount: snapshot.result.citations?.length,
                claimCount: snapshot.result.claims?.length,
                factCheckCount: snapshot.result.fact_checks?.length,
                criticScore: snapshot.result.critic_score ?? null,
              }}
              onCitationRef={handleCitationRef}
            />
          </div>

          {/* Traceability rail */}
          <TraceabilityRail
            sources={snapshot.result.sources}
            evidence={snapshot.result.evidence}
            citations={snapshot.result.citations}
            factChecks={snapshot.result.fact_checks}
            claims={snapshot.result.claims}
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
