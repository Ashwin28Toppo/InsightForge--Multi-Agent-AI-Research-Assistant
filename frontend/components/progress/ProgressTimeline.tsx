"use client";

import React from "react";
import {
  Layers,
  Search,
  FileText,
  ListChecks,
  ShieldCheck,
  Bookmark,
  Activity,
  PenTool,
  Eye,
  CheckCircle2,
  CircleDot,
  Circle,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

export interface ProgressStage {
  key: string;
  label: string;
  desc?: string;
}

interface ProgressTimelineProps {
  /** Ordered stage list. MUST be dynamic — the graph can repeat stages (loops). */
  stages: ProgressStage[];
  /** The most recent in-progress stage key (from current_step). */
  currentStep: string | null;
  /** Ordered list of completed stage keys (from completed_steps). */
  completedSteps: string[];
}

/** Icon lookup by stage key; falls back to Circle for unknown/custom stages. */
const STAGE_ICONS: Record<string, LucideIcon> = {
  plan: Layers,
  research: Search,
  evidence: FileText,
  claim_extraction: ListChecks,
  fact_check: ShieldCheck,
  citation: Bookmark,
  confidence: Activity,
  writer: PenTool,
  critic: Eye,
};

export default function ProgressTimeline({
  stages,
  currentStep,
  completedSteps,
}: ProgressTimelineProps) {
  // Positional completion: completed_steps is an ordered list, so stage at
  // index i is done when i < completedSteps.length. This correctly handles
  // repeated stage keys (e.g. a second "research" pass from the loop).
  const getStepStatus = (index: number, key: string) => {
    if (index < completedSteps.length) return "completed";
    if (key === currentStep) return "active";
    return "pending";
  };

  const allDone =
    stages.length > 0 && completedSteps.length >= stages.length;

  // The activity line mirrors the positional highlight: the stage matching
  // current_step, or the next pending stage when no step is reported yet.
  const activeIndex = stages.findIndex((s) => s.key === currentStep);
  const activityStage =
    activeIndex >= 0 ? stages[activeIndex] : stages[completedSteps.length];

  return (
    <div className="w-full bg-card border border-border rounded-xl p-5 md:p-6">
      <div className="flex items-center justify-between mb-6 gap-3 flex-wrap">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground font-mono">
            Pipeline Activity
          </h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            {completedSteps.length} of {stages.length} stages completed
          </p>
        </div>
        <div
          className={`px-2.5 py-1 rounded-md bg-muted border text-[10px] font-mono font-semibold uppercase select-none ${
            allDone
              ? "border-success/30 text-success"
              : "border-border text-primary"
          }`}
        >
          {currentStep
            ? `Running: ${activityStage?.label ?? currentStep}`
            : allDone
              ? "Complete"
              : "Idle"}
        </div>
      </div>

      <ol className="relative">
        {/* Connector line (desktop) */}
        <div
          className="absolute top-5 left-6 right-6 h-0.5 bg-border hidden md:block"
          aria-hidden="true"
        />

        <div className="grid grid-cols-1 md:grid-cols-9 gap-4 md:gap-2">
          {stages.map((stage, idx) => {
            const status = getStepStatus(idx, stage.key);
            const Icon = STAGE_ICONS[stage.key] ?? Circle;

            return (
              <li
                key={`${stage.key}-${idx}`}
                className="flex md:flex-col items-center gap-3 md:gap-2 text-left md:text-center"
              >
                {/* Node bubble */}
                <div
                  className={`h-10 w-10 rounded-full flex items-center justify-center border transition-all duration-300 relative shrink-0
                    ${status === "completed"
                      ? "bg-primary/10 border-primary text-primary"
                      : status === "active"
                        ? "bg-background border-primary text-primary active-pulse motion-reduce:animate-none ring-2 ring-primary/20 scale-105"
                        : "bg-background border-border text-muted-foreground"
                    }`}
                  aria-current={status === "active" ? "step" : undefined}
                >
                  {status === "completed" ? (
                    <CheckCircle2
                      size={18}
                      className="stroke-[2.5]"
                      aria-label="completed"
                    />
                  ) : status === "active" ? (
                    <CircleDot
                      size={18}
                      className="animate-spin duration-3000 motion-reduce:animate-none"
                      aria-label="active"
                    />
                  ) : (
                    <Icon size={16} aria-hidden="true" />
                  )}

                  {/* Step index (desktop) */}
                  <span className="absolute -top-6 text-[9px] font-mono font-bold text-muted-foreground hidden md:inline select-none">
                    {String(idx + 1).padStart(2, "0")}
                  </span>
                </div>

                {/* Text details */}
                <div className="flex-1 md:flex-none min-w-0">
                  <h3
                    className={`text-xs font-semibold font-mono tracking-tight transition-colors
                      ${status === "active" || status === "completed"
                        ? "text-foreground"
                        : "text-muted-foreground"
                      }`}
                  >
                    {stage.label}
                  </h3>
                  {stage.desc && (
                    <p className="text-[10px] text-muted-foreground font-sans line-clamp-1 md:hidden lg:line-clamp-2 md:mt-0.5">
                      {stage.desc}
                    </p>
                  )}
                </div>
              </li>
            );
          })}
        </div>
      </ol>

      {/* Current activity — answers “which stage is running right now?” */}
      <div className="mt-5 pt-4 border-t border-border flex items-center justify-between gap-3 flex-wrap">
        <p className="text-xs text-muted-foreground min-w-0">
          {activityStage ? (
            <>
              <span className="font-mono font-semibold uppercase tracking-wider text-primary">
                Active
              </span>
              <span className="ml-2 font-medium text-foreground/90">
                {activityStage.label}
              </span>
              {activityStage.desc && (
                <span className="ml-2 hidden sm:inline text-muted-foreground">
                  — {activityStage.desc}
                </span>
              )}
            </>
          ) : allDone ? (
            <span className="font-semibold text-success">
              All stages complete
            </span>
          ) : (
            <span>Waiting for the worker to report a step…</span>
          )}
        </p>
        <span className="text-[10px] font-mono text-muted-foreground select-none shrink-0">
          {completedSteps.length}/{stages.length}
        </span>
      </div>
    </div>
  );
}
