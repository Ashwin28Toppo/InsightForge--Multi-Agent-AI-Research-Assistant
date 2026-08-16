"use client";

import React from "react";
import { Calendar, Clock, Trash2 } from "lucide-react";
import StatusBadge from "@/components/ui/StatusBadge";
import ConfidenceBadge from "@/components/ui/ConfidenceBadge";
import type { JobStatus } from "@/lib/types/api";

export interface HistoryItemView {
  jobId: string;
  query: string;
  status: JobStatus;
  date: string;
  duration?: string;
  confidence?: string;
  snippet?: string;
}

interface HistoryItemProps {
  item: HistoryItemView;
  onOpen: (jobId: string) => void;
  onDelete: (jobId: string) => void;
}

export default function HistoryItem({ item, onOpen, onDelete }: HistoryItemProps) {
  return (
    <div
      onClick={() => onOpen(item.jobId)}
      className="p-5 bg-card hover:bg-muted/20 border border-border hover:border-border-strong rounded-xl cursor-pointer transition-all flex flex-col sm:flex-row items-start justify-between gap-4 group"
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onOpen(item.jobId);
        }
      }}
      aria-label={`Open research: ${item.query}`}
    >
      <div className="space-y-2 flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap text-[10px] font-mono text-muted-foreground">
          <span className="inline-flex items-center gap-1">
            <Calendar size={12} />
            {item.date}
          </span>
          {item.duration && (
            <>
              <span aria-hidden="true">•</span>
              <span className="inline-flex items-center gap-1">
                <Clock size={12} />
                Duration: {item.duration}
              </span>
            </>
          )}
        </div>

        <h3 className="text-sm font-semibold text-foreground leading-normal group-hover:text-primary transition-colors truncate">
          {item.query}
        </h3>

        {item.snippet && (
          <p className="text-xs text-muted-foreground line-clamp-2 leading-relaxed">
            {item.snippet}
          </p>
        )}
      </div>

      {/* Right side status/actions */}
      <div className="flex sm:flex-col items-center sm:items-end justify-between sm:justify-start w-full sm:w-auto shrink-0 gap-3 border-t sm:border-t-0 border-border pt-3 sm:pt-0">
        <div className="flex items-center gap-2">
          <StatusBadge status={item.status} />
          {item.status === "completed" && (
            <ConfidenceBadge confidence={item.confidence} />
          )}
        </div>

        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onDelete(item.jobId);
          }}
          className="p-2 text-muted-foreground hover:text-destructive hover:bg-destructive/10 rounded-lg cursor-pointer transition-all"
          title="Delete record"
          aria-label={`Delete research: ${item.query}`}
        >
          <Trash2 size={15} />
        </button>
      </div>
    </div>
  );
}
