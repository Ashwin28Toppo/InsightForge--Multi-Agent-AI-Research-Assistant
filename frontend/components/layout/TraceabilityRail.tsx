"use client";

import React, { useState } from "react";
import { ExternalLink } from "lucide-react";
import type { Evidence, Citation, FactCheck } from "@/lib/types/api";
import { getDomain } from "@/lib/utils/url";
import EvidencePanel from "@/components/evidence/EvidencePanel";
import CitationPanel from "@/components/citations/CitationPanel";
import FactCheckList from "@/components/claims/FactCheckList";
import EmptyState from "@/components/feedback/EmptyState";

export type RailTab = "sources" | "evidence" | "citations" | "claims";

const TABS: { key: RailTab; label: string }[] = [
  { key: "sources", label: "Sources" },
  { key: "evidence", label: "Evidence" },
  { key: "citations", label: "Citations" },
  { key: "claims", label: "Claims" },
];

interface TraceabilityRailProps {
  sources?: string[];
  evidence?: Evidence[];
  citations?: Citation[];
  factChecks?: FactCheck[];
  claims?: string[];
  /** Highlight a citation (e.g. when an inline [n] is clicked). */
  activeCitation?: number | null;
  onSelectCitation?: (index: number) => void;
  /** Optional controlled tab (defaults to internal state). */
  activeTab?: RailTab | null;
  onTabChange?: (tab: RailTab) => void;
}

export default function TraceabilityRail({
  sources = [],
  evidence = [],
  citations = [],
  factChecks = [],
  claims = [],
  activeCitation = null,
  onSelectCitation,
  activeTab: controlledTab = null,
  onTabChange,
}: TraceabilityRailProps) {
  const [internalTab, setInternalTab] = useState<RailTab>(
    citations.length > 0 ? "citations" : "sources"
  );
  const activeTab = controlledTab ?? internalTab;

  const setTab = (tab: RailTab) => {
    if (onTabChange) {
      onTabChange(tab);
    } else {
      setInternalTab(tab);
    }
  };

  return (
    <aside className="w-full lg:w-96 border-t lg:border-t-0 lg:border-l border-border bg-sidebar flex flex-col min-w-0 h-[28rem] lg:h-auto overflow-hidden">
      {/* Tab bar */}
      <div
        className="flex border-b border-border bg-background/30 overflow-x-auto shrink-0 select-none"
        role="tablist"
        aria-label="Traceability panels"
      >
        {TABS.map((tab) => (
          <button
            key={tab.key}
            role="tab"
            aria-selected={activeTab === tab.key}
            onClick={() => setTab(tab.key)}
            className={`flex-1 min-w-[72px] py-3.5 px-2 text-center text-[10px] font-mono font-bold uppercase tracking-wider border-b-2 cursor-pointer transition-all
              ${activeTab === tab.key
                ? "border-primary text-primary bg-card"
                : "border-transparent text-muted-foreground hover:text-foreground"
              }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Active panel */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4" role="tabpanel">
        {activeTab === "sources" && (
          <div className="space-y-2">
            {sources.length === 0 ? (
              <EmptyState
                title="No sources"
                body="This run produced no source URLs."
                icon={<ExternalLink size={18} />}
              />
            ) : (
              sources.map((source, idx) => (
                <a
                  key={`${source}-${idx}`}
                  href={source}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center justify-between p-3 bg-card border border-border hover:border-border-strong rounded-xl text-xs text-muted-foreground hover:text-foreground cursor-pointer transition-all group"
                >
                  <span className="min-w-0">
                    <span className="block truncate pr-4 font-mono text-[10px]">
                      {source}
                    </span>
                    <span className="block text-[9px] font-mono text-primary truncate">
                      {getDomain(source)}
                    </span>
                  </span>
                  <ExternalLink
                    size={12}
                    className="shrink-0 text-muted-foreground group-hover:text-foreground"
                  />
                </a>
              ))
            )}
          </div>
        )}

        {activeTab === "evidence" && <EvidencePanel evidence={evidence} />}

        {activeTab === "citations" && (
          <CitationPanel
            citations={citations}
            activeIndex={activeCitation}
            onSelect={onSelectCitation}
          />
        )}

        {activeTab === "claims" && (
          <div className="space-y-3">
            <FactCheckList checks={factChecks} />
            {claims.length > 0 && (
              <div className="pt-2">
                <p className="text-[10px] font-mono font-bold uppercase tracking-wider text-muted-foreground mb-2">
                  Extracted Claims
                </p>
                <ul className="space-y-1.5">
                  {claims.map((claim, idx) => (
                    <li
                      key={idx}
                      className="flex gap-2 text-xs text-foreground/90 leading-relaxed"
                    >
                      <span className="text-primary font-mono text-[10px] mt-0.5 select-none">
                        {String(idx + 1).padStart(2, "0")}
                      </span>
                      <span>{claim}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>
    </aside>
  );
}
