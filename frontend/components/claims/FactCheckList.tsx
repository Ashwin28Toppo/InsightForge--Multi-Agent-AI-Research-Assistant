"use client";

import React from "react";
import { ShieldCheck, ShieldX, SearchCheck, HelpCircle, CheckCircle2 } from "lucide-react";
import type { FactCheck } from "@/lib/types/api";
import EmptyState from "@/components/feedback/EmptyState";

/** Verdict badge — icon + text, never color alone. */
export function VerdictBadge({ verdict }: { verdict?: string }) {
  const v = verdict ? verdict.toLowerCase() : "";

  let icon = <HelpCircle size={11} />;
  let label = verdict || "Unchecked";
  let classes = "border-border-strong bg-muted text-muted-foreground";

  if (v === "supported" || v === "verified") {
    icon = <CheckCircle2 size={11} />;
    label = "Verified";
    classes = "border-success/30 bg-success/5 text-success";
  } else if (v === "unsupported") {
    icon = <ShieldX size={11} />;
    label = "Unsupported";
    classes = "border-destructive/30 bg-destructive/5 text-destructive";
  } else if (v.includes("research") || v.includes("unclear") || v === "needs more research") {
    icon = <SearchCheck size={11} />;
    label = "Needs research";
    classes = "border-warning/30 bg-warning/5 text-warning";
  } else if (v === "unverified") {
    icon = <ShieldCheck size={11} />;
    label = "Unverified";
    classes = "border-warning/30 bg-warning/5 text-warning";
  }

  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full border text-[9px] font-mono font-bold uppercase tracking-wide select-none ${classes}`}
    >
      {icon}
      <span>{label}</span>
    </span>
  );
}

export default function FactCheckList({
  checks,
  className = "",
}: {
  checks: FactCheck[];
  className?: string;
}) {
  if (checks.length === 0) {
    return (
      <EmptyState
        title="No fact checks"
        body="This run produced no claim-level verifications."
        icon={<ShieldCheck size={18} />}
      />
    );
  }
  return (
    <div className={`space-y-3 ${className}`}>
      {checks.map((check, idx) => (
        <div key={idx} className="p-3.5 bg-card border border-border rounded-xl space-y-3">
          <div className="flex items-start gap-1.5">
            <span className="mt-0.5 text-primary font-mono text-[10px] select-none" aria-hidden="true">
              “
            </span>
            <p className="text-xs font-semibold text-foreground leading-normal">
              {check.claim}
            </p>
            <span className="mt-0.5 text-primary font-mono text-[10px] select-none" aria-hidden="true">
              ”
            </span>
          </div>

          <div className="flex items-center justify-between gap-2 flex-wrap text-[10px] font-mono">
            <div className="flex items-center gap-2">
              <VerdictBadge verdict={check.verdict} />
              {typeof check.confidence === "number" && (
                <span className="text-muted-foreground">
                  Conf: {Math.round(check.confidence * 100)}%
                </span>
              )}
            </div>
            {(check.evidence_refs?.length ?? 0) > 0 && (
              <div className="flex gap-1">
                {check.evidence_refs!.map((ref) => (
                  <span
                    key={ref}
                    className="px-1.5 py-0.5 rounded bg-muted border border-border text-primary text-[8px] font-bold"
                  >
                    {ref}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
