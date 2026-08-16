"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import AppShell from "@/components/layout/AppShell";
import HistoryItem, { HistoryItemView } from "@/components/history/HistoryItem";
import EmptyState from "@/components/feedback/EmptyState";
import Skeleton from "@/components/feedback/Skeleton";
import { History, Search } from "lucide-react";
import { getHistory, deleteHistoryItem } from "@/lib/history/store";

type StatusFilter = "all" | "completed" | "failed";

export default function HistoryPage() {
  const router = useRouter();
  const [items, setItems] = useState<HistoryItemView[] | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");

  // Load once (post-hydration — localStorage is client-only). Records are
  // written by the research workspace when jobs reach a terminal state.
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- client-only localStorage read must happen after hydration
    setItems(
      getHistory().map((h) => ({
        jobId: h.jobId,
        query: h.query,
        status: h.status,
        date: h.completedAt,
        duration: h.duration,
        confidence: h.confidence,
        snippet: h.reportSnippet,
      }))
    );
  }, []);

  const handleDelete = (jobId: string) => {
    deleteHistoryItem(jobId);
    setItems((prev) => (prev ? prev.filter((i) => i.jobId !== jobId) : prev));
  };

  const filteredItems = (items ?? []).filter((item) => {
    const matchesQuery = item.query
      .toLowerCase()
      .includes(searchQuery.toLowerCase());
    const matchesStatus =
      statusFilter === "all" || item.status === statusFilter;
    return matchesQuery && matchesStatus;
  });

  return (
    <AppShell>
      <div className="flex-1 max-w-5xl w-full mx-auto px-6 py-10 space-y-6">
        {/* Header */}
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

        {/* Controls */}
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

        {/* List */}
        {items === null ? (
          <div className="bg-card border border-border rounded-xl p-5 space-y-4">
            <Skeleton lines={2} />
            <Skeleton lines={2} />
            <Skeleton lines={2} />
          </div>
        ) : filteredItems.length > 0 ? (
          <div className="space-y-3">
            {filteredItems.map((item) => (
              <HistoryItem
                key={item.jobId}
                item={item}
                onOpen={(jobId) => router.push(`/history/${jobId}`)}
                onDelete={handleDelete}
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
    </AppShell>
  );
}
