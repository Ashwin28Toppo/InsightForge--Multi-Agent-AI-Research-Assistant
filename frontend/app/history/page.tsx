"use client";

import React, { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import AppShell from "@/components/layout/AppShell";
import HistoryItem, { HistoryItemView } from "@/components/history/HistoryItem";
import EmptyState from "@/components/feedback/EmptyState";
import Skeleton from "@/components/feedback/Skeleton";
import AuthGate from "@/components/auth/AuthGate";
import { History, Search, RefreshCw } from "lucide-react";
import { getResearchHistory } from "@/lib/api/research";
import { apiErrorMessage } from "@/lib/utils/errors";
import type { ResearchHistoryItem } from "@/lib/types/api";

type StatusFilter = "all" | "completed" | "failed";

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

function toView(job: ResearchHistoryItem): HistoryItemView {
  return {
    jobId: job.job_id,
    query: job.query,
    status: job.status,
    date: formatDateTime(job.created_at),
    updatedAt: formatDateTime(job.updated_at),
    currentStep: job.current_step ?? undefined,
    completedSteps: job.completed_steps ?? [],
    confidence: job.result?.confidence,
    snippet: job.result?.report ? job.result.report.slice(0, 240) : undefined,
    error: job.error,
  };
}

function HistoryContent() {
  const router = useRouter();
  const [items, setItems] = useState<HistoryItemView[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");

  const load = useCallback(async () => {
    setLoadError(null);
    setItems(null);
    try {
      const res = await getResearchHistory();
      setItems(res.jobs.map(toView));
    } catch (err) {
      setLoadError(apiErrorMessage(err));
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- fetch must reset loading state; same pattern as the rest of the app
    void load();
  }, [load]);

  const filteredItems = (items ?? []).filter((item) => {
    const matchesQuery = item.query
      .toLowerCase()
      .includes(searchQuery.toLowerCase());
    const matchesStatus =
      statusFilter === "all" || item.status === statusFilter;
    return matchesQuery && matchesStatus;
  });

  return (
    <div className="flex-1 max-w-5xl w-full mx-auto px-6 py-10 space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-border">
        <div>
          <div className="flex items-center gap-2 text-xs font-mono font-bold text-muted-foreground uppercase tracking-widest">
            <History size={14} />
            <span>Workspace Archives</span>
          </div>
          <h1 className="text-2xl font-bold font-syne tracking-tight mt-1 text-foreground">
            Research History
          </h1>
        </div>
        <span className="px-3 py-1 bg-muted border border-border rounded-lg text-xs font-semibold text-muted-foreground font-mono select-none">
          {items === null ? "—" : `${filteredItems.length} record${filteredItems.length === 1 ? "" : "s"}`}
        </span>
      </div>

      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search
            size={16}
            className="absolute left-3.5 top-1/2 -translate-y-1/2 text-muted-foreground pointer-events-none"
          />
          <input
            type="search"
            placeholder="Search past inquiries…"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-card border border-border focus:border-primary/60 focus:ring-2 focus:ring-primary/10 pl-10 pr-4 py-2.5 rounded-xl text-sm text-foreground placeholder:text-muted-foreground focus:outline-none"
            aria-label="Search research history"
          />
        </div>

        <div
          className="flex items-center gap-1 p-1 rounded-xl bg-card border border-border"
          role="group"
          aria-label="Filter by status"
        >
          {(
            [
              { key: "all", label: "All" },
              { key: "completed", label: "Completed" },
              { key: "failed", label: "Failed" },
            ] as { key: StatusFilter; label: string }[]
          ).map((option) => (
            <button
              key={option.key}
              type="button"
              onClick={() => setStatusFilter(option.key)}
              className={`px-3 py-1.5 rounded-lg text-xs font-mono font-bold uppercase tracking-wider cursor-pointer transition-all
                ${statusFilter === option.key
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:text-foreground"
                }`}
              aria-pressed={statusFilter === option.key}
            >
              {option.label}
            </button>
          ))}
        </div>
      </div>

      {items === null && !loadError ? (
        <div className="bg-card border border-border rounded-xl p-5 space-y-4" aria-busy="true">
          <Skeleton lines={2} />
          <Skeleton lines={2} />
          <Skeleton lines={2} />
        </div>
      ) : loadError ? (
        <div className="bg-card border border-destructive/25 rounded-xl p-8 text-center space-y-4">
          <p className="text-sm font-semibold text-foreground">
            Could not load research history
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
      ) : filteredItems.length > 0 ? (
        <div className="space-y-3">
          {filteredItems.map((item) => (
            <HistoryItem
              key={item.jobId}
              item={item}
              onOpen={(jobId) => router.push(`/history/${jobId}`)}
            />
          ))}
        </div>
      ) : (
        <EmptyState
          title={searchQuery || statusFilter !== "all" ? "No matching archives" : "No research history yet"}
          body={
            searchQuery || statusFilter !== "all"
              ? "No inquiries match your current search or filter criteria."
              : "Submit a research query and completed runs will be archived here."
          }
          tone="info"
          action={
            <button
              type="button"
              onClick={() => router.push("/")}
              className="inline-flex px-4 py-2 bg-primary text-primary-foreground font-semibold text-xs rounded-lg hover:bg-primary/95 cursor-pointer transition-all"
            >
              Start research
            </button>
          }
        />
      )}
    </div>
  );
}

export default function HistoryPage() {
  return (
    <AppShell>
      <AuthGate
        promptTitle="Sign in to view your history"
        promptBody="Research history is stored per user on the server. Sign in to see your past inquiries."
      >
        <HistoryContent />
      </AuthGate>
    </AppShell>
  );
}
