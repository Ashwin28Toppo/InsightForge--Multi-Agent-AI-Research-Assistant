export type JobStatus = "queued" | "running" | "completed" | "failed";

export interface Citation {
  index?: number;             // [1], [2], ...
  source_type?: "web" | "rag";
  title?: string;
  url?: string | null;
  document_id?: string | null;
  page?: number | null;
  chunk_index?: number | null;
}

export interface Evidence {
  id?: string;                // "E1", "E2", ...
  source_type?: "web" | "rag";
  text?: string;              // truncated snippet
  title?: string;
  url?: string | null;
  document_id?: string | null;
  page?: number | null;
  chunk_index?: number | null;
  score?: number;
}

export interface FactCheck {
  claim?: string;
  verdict?: string;           // "supported" | "unsupported" | "needs more research" | ...
  confidence?: number;
  evidence_refs?: string[];   // e.g. ["E1"]
}

export interface ResearchResult {
  query?: string;
  report?: string;            // final markdown report (render with a markdown renderer)
  report_draft?: string;      // internal alias — usually same as report
  search_results?: string;    // raw search summary text
  sources?: string[];         // source URLs
  citations?: Citation[];     // numbered citations
  evidence?: Evidence[];      // evidence items (E1, E2, ...)
  claims?: string[];          // extracted claims
  fact_checks?: FactCheck[];  // claim verdicts
  confidence?: string;        // "high" | "medium" | "low" (or unknown)
  critic_feedback?: string;   // optional critic note
  critic_score?: number | null;
  errors?: string[];          // safe non-fatal errors
}

export interface ResearchJobResponse {
  job_id: string;
  status: "queued";
}

export interface ResearchStatusResponse {
  job_id: string;
  status: JobStatus;
  result?: ResearchResult;
  error?: string;
}

export interface ResearchProgressResponse {
  job_id: string;
  status: JobStatus;
  current_step: string | null;
  completed_steps: string[];
}

export interface SseProgressPayload {
  job_id: string;
  status: JobStatus;
  current_step: string | null;
  completed_steps: string[];
  error?: string;
}
