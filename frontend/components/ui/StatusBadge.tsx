"use client";

import React from "react";
import { Clock, Loader2, CheckCircle2, XCircle } from "lucide-react";
import type { JobStatus } from "@/lib/types/api";

interface StatusBadgeProps {
  status: JobStatus;
  className?: string;
}

const STATUS_CONFIG: Record<
  JobStatus,
  { label: string; icon: React.ReactNode; classes: string }
> = {
  queued: {
    label: "Queued",
    icon: <Clock size={11} />,
    classes: "border-border-strong bg-muted text-muted-foreground",
  },
  running: {
    label: "Running",
    icon: <Loader2 size={11} className="animate-spin" />,
    classes: "border-primary/30 bg-primary/5 text-primary",
  },
  completed: {
    label: "Completed",
    icon: <CheckCircle2 size={11} />,
    classes: "border-success/30 bg-success/5 text-success",
  },
  failed: {
    label: "Failed",
    icon: <XCircle size={11} />,
    classes: "border-destructive/30 bg-destructive/5 text-destructive",
  },
};

export default function StatusBadge({ status, className = "" }: StatusBadgeProps) {
  const config = STATUS_CONFIG[status];
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full border text-[10px] font-mono font-bold uppercase tracking-wide select-none ${config.classes} ${className}`}
    >
      {config.icon}
      <span>{config.label}</span>
    </span>
  );
}
