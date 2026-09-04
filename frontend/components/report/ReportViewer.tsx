"use client";

import React from "react";
import MarkdownRenderer from "./MarkdownRenderer";
import ConfidenceBadge from "@/components/ui/ConfidenceBadge";
import { FileText, Copy, Check, FileDown } from "lucide-react";

export interface ReportMeta {
  elapsed?: string;
  completedAt?: string;
  sourceCount?: number;
  citationCount?: number;
  claimCount?: number;
  factCheckCount?: number;
  criticScore?: number | null;
}

interface ReportViewerProps {
  query?: string;
  report: string;
  confidence?: string;
  meta?: ReportMeta;
  onCitationRef?: (index: number) => void;
  headerActions?: React.ReactNode;
  className?: string;
}

export default function ReportViewer({
  query,
  report,
  confidence,
  meta,
  onCitationRef,
  headerActions,
  className = "",
}: ReportViewerProps) {
  const [copied, setCopied] = React.useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(report);
      setCopied(true);
      setTimeout(() => setCopied(false), 1600);
    } catch {
      // Clipboard unavailable — no-op for the visual foundation.
    }
  };

  const handleExport = () => {
    const blob = new Blob([report], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "insightforge-report.md";
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className={`bg-card border border-border rounded-xl ${className}`}>
      <div className="px-6 md:px-8 py-5 border-b border-border">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3 min-w-0">
            <span className="hidden sm:inline-flex h-8 w-8 shrink-0 rounded-lg bg-primary/10 border border-primary/25 items-center justify-center text-primary">
              <FileText size={15} />
            </span>
            <div className="min-w-0">
              <p className="text-[10px] font-mono font-bold uppercase tracking-widest text-muted-foreground">
                Research Report
              </p>
              <div className="flex items-center gap-2 flex-wrap mt-0.5">
                <ConfidenceBadge confidence={confidence} />
                {meta?.elapsed && (
                  <span className="text-[10px] font-mono text-muted-foreground">
                    {meta.elapsed}
                  </span>
                )}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleCopy}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border hover:border-border-strong text-xs font-medium text-muted-foreground hover:text-foreground cursor-pointer transition-all"
            >
              {copied ? <Check size={13} className="text-success" /> : <Copy size={13} />}
              <span>{copied ? "Copied" : "Copy"}</span>
            </button>
            <button
              type="button"
              onClick={handleExport}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border hover:border-border-strong text-xs font-medium text-muted-foreground hover:text-foreground cursor-pointer transition-all"
            >
              <FileDown size={13} />
              <span>Export</span>
            </button>
            {headerActions}
          </div>
        </div>

        {(meta?.sourceCount != null ||
          meta?.citationCount != null ||
          meta?.claimCount != null ||
          meta?.factCheckCount != null ||
          meta?.criticScore != null ||
          meta?.completedAt) && (
          <div className="flex flex-wrap gap-x-5 gap-y-1 mt-4 pt-3 border-t border-border text-[10px] font-mono text-muted-foreground">
            {query && (
              <span className="truncate max-w-full">
                Query: <span className="text-foreground/80">{query}</span>
              </span>
            )}
            {meta?.sourceCount != null && <span>{meta.sourceCount} sources</span>}
            {meta?.citationCount != null && <span>{meta.citationCount} citations</span>}
            {meta?.claimCount != null && <span>{meta.claimCount} claims</span>}
            {meta?.factCheckCount != null && <span>{meta.factCheckCount} fact checks</span>}
            {meta?.criticScore != null && <span>Critic: {meta.criticScore}/10</span>}
            {meta?.completedAt && <span>Completed: {meta.completedAt}</span>}
          </div>
        )}
      </div>

      <div className="px-6 md:px-10 py-8">
        <div className="max-w-[72ch]">
          <MarkdownRenderer markdown={report} onCitationRef={onCitationRef} />
        </div>
      </div>
    </div>
  );
}
