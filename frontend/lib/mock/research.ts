"use client";

/**
 * Centralized mock data for the Phase 2E visual foundation.
 *
 * Everything here is realistic research output (no lorem ipsum) and is kept
 * separate from the future API integration (lib/api, lib/sse). When real
 * integration lands, pages swap these mocks for the API layer — no component
 * should import this module except pages/hooks during the mock phase.
 */
import { ResearchResult } from "../types/api";

/** Canonical logical pipeline stages surfaced as progress steps. */
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

export const BATTERIES_QUERY =
  "What are the latest advances in solid-state battery electrolytes?";

export const BATTERIES_RESULT: ResearchResult = {
  query: BATTERIES_QUERY,
  report: `# Advances in Solid-State Battery Electrolytes

> Multi-agent synthesis of six peer-reviewed sources. Confidence: high.

## Executive Summary

Solid-state batteries replace flammable liquid organic electrolytes with solid ionic conductors, enabling higher energy density and improved safety [1]. Recent advances concentrate on three material families — sulfide, garnet-oxide, and polymer-ceramic composites — each with distinct conductivity, stability, and processing trade-offs.

## Methodology

The research pipeline queried six peer-reviewed sources, extracted numbered evidence items (E1–E4), and batch-verified each central claim against the evidence before drafting this report.

## Findings

### Garnet-type oxide electrolytes

Cubic-phase Li7La3Zr2O12 (LLZO) garnets exhibit room-temperature ionic conductivity above 1 mS/cm and remain chemically stable against lithium metal [1]. Their mechanical rigidity, however, creates solid-solid contact loss during cycling, producing local current constriction and dendritic short-circuit pathways [3].

### Sulfide electrolytes

Argyrodite-type Li6PS5Cl compresses easily at room temperature, forming intimate electrode contact without sintering [2]. Narrow electrochemical stability windows force protective coatings — thin oxide layers deposited by atomic layer deposition — to prevent interfacial decomposition [2].

### Polymer-ceramic composites

Polymer-in-ceramic membranes (PEO-LiTFSI with LLTO nanofillers) deliver flexible form factors and suppress short-circuit pathways, though at lower bulk conductivity [4].

## Analysis

- Garnets lead on stability and conductivity; sulfides lead on processability.
- No single chemistry dominates — hybrid architectures are the consensus direction.
- Interface engineering, not bulk ionic transport, is the primary bottleneck [3][4].

## Conclusion

Solid-state electrolytes are transitioning from laboratory demonstrations toward manufacturable prototypes. The near-term frontier is interfacial stability and scalable processing rather than raw ionic conductivity.

---

*Prepared by the InsightForge multi-agent pipeline. Citations [1]–[4] resolve in the evidence rail.*`,
  report_draft: "",
  search_results:
    "Synthesized 6 sources across Nature Materials, Energy Storage Materials, Nano-Micro Letters and Advanced Energy Materials covering garnet, sulfide and composite solid electrolytes.",
  sources: [
    "https://doi.org/10.1038/s41563-024-01827-y",
    "https://doi.org/10.1016/j.ensm.2023.01.021",
    "https://doi.org/10.1007/s40820-023-01124-w",
    "https://doi.org/10.1002/aenm.202303411",
    "https://arxiv.org/abs/2306.14636",
    "https://pubs.acs.org/doi/10.1021/acs.chemmater.3c01842",
  ],
  citations: [
    {
      index: 1,
      source_type: "web",
      title: "Next-generation garnet-type solid electrolytes: A review",
      url: "https://doi.org/10.1038/s41563-024-01827-y",
    },
    {
      index: 2,
      source_type: "web",
      title: "Sulfide-based solid-state battery electrolytes: Interfaces and stability",
      url: "https://doi.org/10.1016/j.ensm.2023.01.021",
    },
    {
      index: 3,
      source_type: "web",
      title: "Mechanical contact loss and dendritic growth in oxide solid-state batteries",
      url: "https://doi.org/10.1007/s40820-023-01124-w",
    },
    {
      index: 4,
      source_type: "rag",
      title: "Polymer-ceramic composite electrolytes: Flexibility meets conductivity",
      url: "https://doi.org/10.1002/aenm.202303411",
    },
  ],
  evidence: [
    {
      id: "E1",
      source_type: "web",
      text: "Cubic-phase LLZO garnets exhibit room-temperature ionic conductivity exceeding 1 mS/cm and remain chemically stable when in contact with molten lithium metal.",
      title: "Next-generation garnet-type solid electrolytes: A review",
      url: "https://doi.org/10.1038/s41563-024-01827-y",
      score: 0.94,
    },
    {
      id: "E2",
      source_type: "web",
      text: "Argyrodite-type Li6PS5Cl displays excellent cold-pressability and high initial conductivity, though interface degradation with lithium metal requires protective atomic-layer-deposited coatings.",
      title: "Sulfide-based solid-state battery electrolytes: Interfaces and stability",
      url: "https://doi.org/10.1016/j.ensm.2023.01.021",
      score: 0.91,
    },
    {
      id: "E3",
      source_type: "web",
      text: "Rigid garnet oxides develop micro-contact voids during discharge as lithium is stripped, causing local current constriction and subsequent dendritic short-circuit pathways.",
      title: "Mechanical contact loss and dendritic growth in oxide solid-state batteries",
      url: "https://doi.org/10.1007/s40820-023-01124-w",
      score: 0.88,
    },
    {
      id: "E4",
      source_type: "rag",
      text: "Polymer-in-ceramic membranes combining PEO-LiTFSI with LLTO nanoparticles achieve flexible form factors while reducing dendritic short-circuit pathways, at lower bulk conductivity.",
      title: "Polymer-ceramic composite electrolytes: Flexibility meets conductivity",
      url: "https://doi.org/10.1002/aenm.202303411",
      score: 0.82,
    },
  ],
  claims: [
    "Cubic LLZO garnet electrolytes exceed 1 mS/cm at room temperature.",
    "Sulfide electrolytes require protective coatings to remain stable against lithium metal.",
    "Polymer-ceramic composites completely eliminate dendrite growth.",
    "Interface engineering is the dominant bottleneck in solid-state batteries.",
  ],
  fact_checks: [
    {
      claim: "Cubic LLZO garnet electrolytes exceed 1 mS/cm at room temperature.",
      verdict: "supported",
      confidence: 0.95,
      evidence_refs: ["E1"],
    },
    {
      claim: "Sulfide electrolytes require protective coatings to remain stable against lithium metal.",
      verdict: "supported",
      confidence: 0.88,
      evidence_refs: ["E2"],
    },
    {
      claim: "Polymer-ceramic composites completely eliminate dendrite growth.",
      verdict: "unsupported",
      confidence: 0.64,
      evidence_refs: ["E4"],
    },
    {
      claim: "Interface engineering is the dominant bottleneck in solid-state batteries.",
      verdict: "needs more research",
      confidence: 0.71,
      evidence_refs: ["E1", "E3"],
    },
  ],
  confidence: "high",
  critic_feedback:
    "Score: 8/10 — strong source coverage; consider quantifying cost/scale trade-offs in the conclusion.",
  critic_score: 8,
  errors: [],
};

export const REASONING_QUERY =
  "How do chain-of-thought and process supervision improve reasoning in large language models?";

export const REASONING_RESULT: ResearchResult = {
  query: REASONING_QUERY,
  report: `# Reasoning Methods in Frontier Language Models

> Multi-agent synthesis of three primary sources. Confidence: medium.

## Executive Summary

Large language models improve at multi-step reasoning when prompted to emit intermediate steps and when trained or evaluated on the correctness of those steps. Two mechanisms dominate the literature: chain-of-thought prompting and process supervision.

## Key Findings

- Chain-of-thought (CoT) prompting elicits step-by-step reasoning and substantially improves arithmetic and logic benchmarks in sufficiently large models [1].
- Zero-shot activation ("let's think step by step") unlocks reasoning paths without few-shot exemplars [2].
- Process supervision — rewarding correct intermediate steps rather than only the final answer — reduces hallucinated reasoning chains in complex mathematical tasks [3].

## Analysis

CoT redistributes computation toward the search space of intermediate tokens. Verification moves the bottleneck from answer correctness to step correctness, which is more label-efficient and better aligned with human review.

## Conclusion

Reasoning quality in frontier models is driven as much by prompting and supervision strategy as by scale. Process-supervised verifiers are the most promising near-term lever.

---

*Prepared by the InsightForge multi-agent pipeline. Citations [1]–[3] resolve in the evidence rail.*`,
  report_draft: "",
  search_results:
    "Synthesized 3 sources covering chain-of-thought prompting, zero-shot reasoning activation, and process-supervised verifiers.",
  sources: [
    "https://arxiv.org/abs/2201.11903",
    "https://arxiv.org/abs/2205.11916",
    "https://arxiv.org/abs/2305.20050",
  ],
  citations: [
    {
      index: 1,
      source_type: "web",
      title: "Chain-of-Thought Prompting Elicits Reasoning in Large Language Models",
      url: "https://arxiv.org/abs/2201.11903",
    },
    {
      index: 2,
      source_type: "web",
      title: "Large Language Models are Zero-Shot Reasoners",
      url: "https://arxiv.org/abs/2205.11916",
    },
    {
      index: 3,
      source_type: "web",
      title: "Let's Verify Step by Step",
      url: "https://arxiv.org/abs/2305.20050",
    },
  ],
  evidence: [
    {
      id: "E1",
      source_type: "web",
      text: "Few-shot examples presenting step-by-step reasoning paths trigger multi-step reasoning outputs in models above roughly 100B parameters.",
      title: "Chain-of-Thought Prompting Elicits Reasoning in Large Language Models",
      url: "https://arxiv.org/abs/2201.11903",
      score: 0.97,
    },
    {
      id: "E2",
      source_type: "web",
      text: "Appending the instruction 'let's think step by step' acts as a zero-shot activator for complex reasoning pathways without few-shot examples.",
      title: "Large Language Models are Zero-Shot Reasoners",
      url: "https://arxiv.org/abs/2205.11916",
      score: 0.89,
    },
    {
      id: "E3",
      source_type: "web",
      text: "Process supervision, which rewards correct intermediate reasoning steps, reduces hallucinations on complex math benchmarks compared with outcome supervision.",
      title: "Let's Verify Step by Step",
      url: "https://arxiv.org/abs/2305.20050",
      score: 0.91,
    },
  ],
  claims: [
    "CoT prompting improves multi-step mathematical benchmarks in large models.",
    "Zero-shot activation matches few-shot CoT prompting across all test suites.",
    "Process supervision yields higher accuracy than outcome supervision on math benchmarks.",
  ],
  fact_checks: [
    {
      claim: "CoT prompting improves multi-step mathematical benchmarks in large models.",
      verdict: "supported",
      confidence: 0.98,
      evidence_refs: ["E1"],
    },
    {
      claim: "Zero-shot activation matches few-shot CoT prompting across all test suites.",
      verdict: "unsupported",
      confidence: 0.89,
      evidence_refs: ["E2"],
    },
    {
      claim: "Process supervision yields higher accuracy than outcome supervision on math benchmarks.",
      verdict: "supported",
      confidence: 0.91,
      evidence_refs: ["E3"],
    },
  ],
  confidence: "medium",
  critic_feedback:
    "Score: 7/10 — solid primary sources; note the narrow benchmark coverage.",
  critic_score: 7,
  errors: [],
};

export interface MockHistoryRecord {
  jobId: string;
  query: string;
  status: "completed" | "failed" | "running";
  date: string;
  duration: string;
  confidence?: "high" | "medium" | "low";
  snippet: string;
  topic: "batteries" | "reasoning" | "carbon" | "hydrides" | "fusion";
}

export const MOCK_HISTORY: MockHistoryRecord[] = [
  {
    jobId: "mock-batteries-01",
    query: BATTERIES_QUERY,
    status: "completed",
    date: "August 16, 2026",
    duration: "01:14",
    confidence: "high",
    snippet:
      "Solid-state batteries replace flammable liquid electrolytes with solid ionic conductors. Garnet, sulfide and composite chemistries lead current research, with interface engineering as the dominant bottleneck.",
    topic: "batteries",
  },
  {
    jobId: "mock-reasoning-02",
    query: REASONING_QUERY,
    status: "completed",
    date: "August 15, 2026",
    duration: "02:45",
    confidence: "medium",
    snippet:
      "Chain-of-thought prompting and process supervision are the two dominant mechanisms improving multi-step reasoning in frontier language models.",
    topic: "reasoning",
  },
  {
    jobId: "mock-carbon-03",
    query: "What is the carbon sequestration efficiency of kelp farming?",
    status: "completed",
    date: "August 13, 2026",
    duration: "00:52",
    confidence: "high",
    snippet:
      "Kelp aquaculture is a promising biological tool for ocean carbon dioxide removal. Net sequestration depends on detrital export to deep water and harvest accounting.",
    topic: "carbon",
  },
  {
    jobId: "mock-hydrides-04",
    query: "What is the status of room-temperature superconductivity in hydride materials?",
    status: "failed",
    date: "August 10, 2026",
    duration: "01:05",
    confidence: "low",
    snippet:
      "The pipeline failed during the citation stage due to a server-side rate limit (Groq TPM budget exceeded).",
    topic: "hydrides",
  },
  {
    jobId: "mock-fusion-05",
    query: "What are the engineering barriers to commercial fusion power?",
    status: "completed",
    date: "August 08, 2026",
    duration: "01:58",
    confidence: "medium",
    snippet:
      "Breeding blanket tritium self-sufficiency, divertor heat exhaust and neutron-tolerant materials remain the principal engineering barriers to commercial fusion.",
    topic: "fusion",
  },
];

/** Map a mock history topic to its full ResearchResult. */
export function resultForTopic(topic: MockHistoryRecord["topic"]): ResearchResult {
  switch (topic) {
    case "batteries":
      return BATTERIES_RESULT;
    case "reasoning":
      return REASONING_RESULT;
    default:
      return { ...BATTERIES_RESULT, query: BATTERIES_QUERY };
  }
}

/**
 * Simulate the research pipeline running over the canonical stages.
 * Yields an onStep callback per logical stage (like the SSE stream will)
 * and resolves with a full ResearchResult.
 */
export function runMockResearch(
  query: string,
  onStep?: (step: string) => void,
  stepDelayMs = 900
): Promise<ResearchResult> {
  const result: ResearchResult = { ...BATTERIES_RESULT, query };
  return new Promise((resolve) => {
    let index = 0;
    const timer = setInterval(() => {
      if (index < PIPELINE_STAGES.length) {
        onStep?.(PIPELINE_STAGES[index].key);
        index += 1;
      } else {
        clearInterval(timer);
        resolve(result);
      }
    }, stepDelayMs);
  });
}
