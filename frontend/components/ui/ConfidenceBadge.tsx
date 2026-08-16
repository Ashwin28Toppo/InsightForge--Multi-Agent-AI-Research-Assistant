"use client";

import React from "react";
import { Gauge, TrendingUp, Minus, HelpCircle } from "lucide-react";

interface ConfidenceBadgeProps {
  /** "high" | "medium" | "low" | anything else (treated as unknown). */
  confidence?: string;
  className?: string;
}

const TONES: Record<
  string,
  { label: string; icon: React.ReactNode; classes: string }
> = {
  high: {
    label: "High",
    icon: <TrendingUp size={11} />,
    classes: "border-success/30 bg-success/5 text-success",
  },
  medium: {
    label: "Medium",
    icon: <Gauge size={11} />,
    classes: "border-primary/30 bg-primary/5 text-primary",
  },
  low: {
    label: "Low",
    icon: <Minus size={11} />,
    classes: "border-warning/30 bg-warning/5 text-warning",
  },
};

export default function ConfidenceBadge({
  confidence,
  className = "",
}: ConfidenceBadgeProps) {
  const key = confidence ? confidence.toLowerCase() : "";
  const tone = TONES[key] ?? {
    label: confidence || "Unknown",
    icon: <HelpCircle size={11} />,
    classes: "border-border-strong bg-muted text-muted-foreground",
  };

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full border text-[10px] font-mono font-bold uppercase tracking-wide select-none ${tone.classes} ${className}`}
    >
      {tone.icon}
      <span>{tone.label}</span>
    </span>
  );
}
