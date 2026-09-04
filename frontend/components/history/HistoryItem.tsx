"use client";

import React, { useState, useRef, useEffect } from "react";
import { Calendar, Clock, Trash2, AlertCircle } from "lucide-react";
import StatusBadge from "@/components/ui/StatusBadge";
import ConfidenceBadge from "@/components/ui/ConfidenceBadge";
import type { JobStatus } from "@/lib/types/api";

export interface HistoryItemView {
  jobId: string;
  query: string;
  status: JobStatus;
  date: string;
  updatedAt?: string;
  duration?: string;
  confidence?: string;
  snippet?: string;
  currentStep?: string;
  completedSteps?: string[];
  error?: string;
}

interface HistoryItemProps {
  item: HistoryItemView;
  onOpen: (jobId: string) => void;
  onDelete?: (jobId: string) => void;
}

export default function HistoryItem({ item, onOpen, onDelete }: HistoryItemProps) {
  const [confirming, setConfirming] = useState(false);
  const confirmTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Clear any pending auto-disarm timer on unmount.
  useEffect(() => {
    return () => {
      if (confirmTimer.current) clearTimeout(confirmTimer.current);
    };
  }, []);

  const handleDeleteClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!onDelete) return;
    if (!confirming) {
      setConfirming(true);
      confirmTimer.current = setTimeout(() => setConfirming(false), 2500);
      return;
    }
    if (confirmTimer.current) clearTimeout(confirmTimer.current);
    onDelete(item.jobId);
  };

  const stepCount = item.completedSteps?.length ?? 0;

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
          {item.updatedAt && (
            <>
              <span aria-hidden="true">•</span>
              <span className="inline-flex items-center gap-1">
                <Clock size={12} />
                Updated: {item.updatedAt}
              </span>
            </>
          )}
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

        <h3 className="text-sm font-semibold text-foreground leading-normal group-hover:text-primary transition-colors line-clamp-2">
          {item.query}
        </h3>

        {item.snippet && (
          <p className="text-xs text-muted-foreground line-clamp-2 leading-relaxed">
            {item.snippet}
          </p>
        )}

        {(item.currentStep || stepCount > 0) && (
          <div className="flex items-center gap-1.5 flex-wrap">
            {item.currentStep && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-muted border border-border text-[10px] font-mono text-muted-foreground">
                <Clock size={10} />
                STEP: {item.currentStep}
              </span>
            )}
            {stepCount > 0 && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-muted border border-border text-[10px] font-mono text-muted-foreground">
                {stepCount} stage{stepCount === 1 ? "" : "s"}
              </span>
            )}
          </div>
        )}

        {item.status === "failed" && item.error && (
          <p className="flex items-start gap-1.5 text-xs text-destructive leading-relaxed">
            <AlertCircle size={13} className="mt-0.5 shrink-0" />
            <span className="line-clamp-2">{item.error}</span>
          </p>
        )}
      </div>

      <div className="flex sm:flex-col items-center sm:items-end justify-between sm:justify-start w-full sm:w-auto shrink-0 gap-3 border-t sm:border-t-0 border-border pt-3 sm:pt-0">
        <div className="flex items-center gap-2">
          <StatusBadge status={item.status} />
          {item.status === "completed" && (
            <ConfidenceBadge confidence={item.confidence} />
          )}
        </div>

        {onDelete && (
          <button
            type="button"
            onClick={handleDeleteClick}
            className={`p-2 rounded-lg cursor-pointer transition-all ${
            confirming
              ? "text-destructive bg-destructive/10 border border-destructive/30"
              : "text-muted-foreground hover:text-destructive hover:bg-destructive/10 border border-transparent"
          }`}
          title={confirming ? "Click again to confirm deletion" : "Delete record"}
          aria-label={
            confirming
              ? `Confirm delete research: ${item.query}`
              : `Delete research: ${item.query}`
          }
        >
          {confirming ? (
            <span className="text-[10px] font-mono font-bold px-0.5">
              Confirm?
            </span>
          ) : (
            <Trash2 size={15} />
          )}
          </button>
        )}
      </div>
    </div>
  );
}
