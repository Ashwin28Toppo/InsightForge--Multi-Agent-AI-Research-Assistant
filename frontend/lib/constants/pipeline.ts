/**
 * Canonical logical pipeline stages surfaced as progress steps.
 *
 * These are STATIC labels/descriptions for the pipeline timeline and the
 * landing overview — not mock results. The ordered `completed_steps` list
 * from the backend is open-ended (stages may repeat when the research loop
 * is enabled), so callers must treat this as a label map, never a fixed
 * step count.
 */
export interface PipelineStage {
  key: string;
  label: string;
  desc: string;
}

export const PIPELINE_STAGES: PipelineStage[] = [
  { key: "plan", label: "Plan", desc: "Formulate angles & scope" },
  { key: "research", label: "Research", desc: "Gather source publications" },
  { key: "evidence", label: "Evidence", desc: "Extract numbered evidence" },
  { key: "claim_extraction", label: "Claims", desc: "Analyze central assertions" },
  { key: "fact_check", label: "Fact Check", desc: "Batch verify evidence" },
  { key: "citation", label: "Citation", desc: "Apply citation footnotes" },
  { key: "confidence", label: "Confidence", desc: "Assess evidence scoring" },
  { key: "writer", label: "Writer", desc: "Generate report text" },
  { key: "critic", label: "Critic", desc: "Review quality & feedback" },
];

/** Human-readable label lookup for any stage key (including repeats). */
export function stageLabel(key: string): string {
  return PIPELINE_STAGES.find((s) => s.key === key)?.label ?? key;
}
