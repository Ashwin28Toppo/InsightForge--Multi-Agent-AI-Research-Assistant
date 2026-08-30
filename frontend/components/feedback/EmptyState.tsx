"use client";

import React from "react";

interface EmptyStateProps {
  title: string;
  body?: string;
  action?: React.ReactNode;
  tone?: "info" | "muted";
  icon?: React.ReactNode;
}

export default function EmptyState({
  title,
  body,
  action,
  tone = "muted",
  icon,
}: EmptyStateProps) {
  return (
    <div className="text-center py-10 px-6 bg-card border border-border border-dashed rounded-xl space-y-3">
      <div
        className={`h-10 w-10 rounded-full flex items-center justify-center mx-auto ${
          tone === "info"
            ? "bg-primary/10 text-primary border border-primary/20"
            : "bg-muted text-muted-foreground border border-border"
        }`}
      >
        {icon}
      </div>
      <div className="space-y-1">
        <p className="text-sm font-semibold text-foreground">{title}</p>
        {body && (
          <p className="text-xs text-muted-foreground max-w-xs mx-auto leading-relaxed">
            {body}
          </p>
        )}
      </div>
      {action && <div className="pt-1">{action}</div>}
    </div>
  );
}
