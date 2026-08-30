"use client";

import React from "react";
import { ExternalLink, Database, Globe, FileText } from "lucide-react";
import type { Evidence } from "@/lib/types/api";
import { getDomain } from "@/lib/utils/url";
import EmptyState from "@/components/feedback/EmptyState";

export function EvidenceCard({ item }: { item: Evidence }) {
  const isRag = item.source_type === "rag";
  return (
    <div className="p-3.5 bg-card border border-border rounded-xl space-y-2.5 hover:border-border-strong transition-all">
      <div className="flex items-center justify-between gap-2 text-[9px] font-mono">
        <div className="flex items-center gap-1.5 min-w-0">
          <span className="px-1.5 py-0.5 rounded bg-muted border border-border text-primary font-bold shrink-0">
            {item.id || "E?"}
          </span>
          <span
            className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded uppercase font-bold shrink-0 ${
              isRag
                ? "bg-info/10 text-info border border-info/20"
                : "bg-primary/10 text-primary border border-primary/20"
            }`}
          >
            {isRag ? <Database size={9} /> : <Globe size={9} />}
            {item.source_type || "web"}
          </span>
          {isRag && (item.page != null || item.chunk_index != null) && (
            <span className="text-muted-foreground truncate">
              {item.page != null ? `p.${item.page}` : ""}
              {item.page != null && item.chunk_index != null ? " · " : ""}
              {item.chunk_index != null ? `ch.${item.chunk_index}` : ""}
            </span>
          )}
        </div>
        {typeof item.score === "number" && (
          <span className="text-muted-foreground shrink-0">
            relevance {Math.round(item.score * 100)}%
          </span>
        )}
      </div>

      {item.title && (
        <h4 className="text-xs font-semibold text-foreground leading-snug">
          {item.title}
        </h4>
      )}

      {item.text && (
        <p className="text-xs text-foreground/90 leading-relaxed italic border-l-2 border-border pl-2.5">
          “{item.text}”
        </p>
      )}

      {item.url && (
        <a
          href={item.url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 text-[10px] text-info hover:underline font-mono cursor-pointer"
        >
          <FileText size={10} />
          <span className="truncate max-w-[220px]">{getDomain(item.url)}</span>
          <ExternalLink size={10} />
        </a>
      )}
    </div>
  );
}

export default function EvidencePanel({
  evidence,
  className = "",
}: {
  evidence: Evidence[];
  className?: string;
}) {
  if (evidence.length === 0) {
    return (
      <EmptyState
        title="No evidence extracted"
        body="This run did not produce discrete evidence items."
        icon={<FileText size={18} />}
      />
    );
  }
  return (
    <div className={`space-y-3 ${className}`}>
      {evidence.map((item) => (
        <EvidenceCard key={item.id || item.text} item={item} />
      ))}
    </div>
  );
}
