"use client";

import React from "react";
import { ExternalLink, Database, Globe } from "lucide-react";
import type { Citation } from "@/lib/types/api";
import { getDomain } from "@/lib/utils/url";
import EmptyState from "@/components/feedback/EmptyState";

export function CitationCard({
  citation,
  active,
  onSelect,
}: {
  citation: Citation;
  active?: boolean;
  onSelect?: (index: number) => void;
}) {
  const isRag = citation.source_type === "rag";
  return (
    <div
      className={`p-3.5 bg-card border rounded-xl space-y-2 transition-all cursor-pointer ${
        active
          ? "border-primary bg-primary/5"
          : "border-border hover:border-border-strong"
      }`}
      onClick={() => onSelect?.(citation.index ?? 0)}
      role={onSelect ? "button" : undefined}
      tabIndex={onSelect ? 0 : undefined}
      onKeyDown={(e) => {
        if (onSelect && (e.key === "Enter" || e.key === " ")) {
          e.preventDefault();
          onSelect(citation.index ?? 0);
        }
      }}
    >
      <div className="flex items-start gap-2">
        <span className="h-5 w-5 shrink-0 rounded bg-primary/10 border border-primary/20 flex items-center justify-center text-[10px] font-bold text-primary font-mono select-none">
          {citation.index}
        </span>
        <h4 className="text-xs font-semibold text-foreground leading-snug">
          {citation.title || "Untitled source"}
        </h4>
      </div>

      <div className="flex items-center gap-2 text-[9px] font-mono text-muted-foreground pl-7">
        <span
          className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded uppercase font-bold ${
            isRag
              ? "bg-info/10 text-info border border-info/20"
              : "bg-primary/10 text-primary border border-primary/20"
          }`}
        >
          {isRag ? <Database size={9} /> : <Globe size={9} />}
          {citation.source_type || "web"}
        </span>
        <span className="truncate">{getDomain(citation.url)}</span>
      </div>

      {citation.url && (
        <a
          href={citation.url}
          target="_blank"
          rel="noopener noreferrer"
          onClick={(e) => e.stopPropagation()}
          className="inline-flex items-center gap-1 text-[9px] text-info hover:underline font-mono pl-7 cursor-pointer"
        >
          <span className="truncate max-w-[220px]">{citation.url}</span>
          <ExternalLink size={9} />
        </a>
      )}
    </div>
  );
}

export default function CitationPanel({
  citations,
  activeIndex,
  onSelect,
  className = "",
}: {
  citations: Citation[];
  activeIndex?: number | null;
  onSelect?: (index: number) => void;
  className?: string;
}) {
  if (citations.length === 0) {
    return (
      <EmptyState
        title="No citations"
        body="This run produced no numbered citations."
        icon={<ExternalLink size={18} />}
      />
    );
  }
  return (
    <div className={`space-y-3 ${className}`}>
      {citations.map((citation) => (
        <CitationCard
          key={citation.index ?? citation.url}
          citation={citation}
          active={activeIndex === citation.index}
          onSelect={onSelect}
        />
      ))}
    </div>
  );
}
