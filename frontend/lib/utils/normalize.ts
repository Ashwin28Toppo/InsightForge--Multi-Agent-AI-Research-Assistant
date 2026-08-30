"use client";

/**
 * Normalize the backend's opaque result dict into the frontend ResearchResult.
 *
 * The backend result is intentionally an opaque dictionary; this adapter
 * defensively maps whatever fields exist and never throws on missing or
 * malformed optional fields. The UI renders empty states when a collection
 * is absent.
 */
import type { Citation, Evidence, FactCheck, ResearchResult } from "../types/api";

function asString(value: unknown): string | undefined {
  return typeof value === "string" ? value : undefined;
}

function asStringArray(value: unknown): string[] {
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === "string")
    : [];
}

function asNumber(value: unknown): number | undefined {
  return typeof value === "number" ? value : undefined;
}

function asNullableString(value: unknown): string | null | undefined {
  return typeof value === "string" || value === null ? value : undefined;
}

function asNullableNumber(value: unknown): number | null | undefined {
  return typeof value === "number" || value === null ? value : undefined;
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object"
    ? (value as Record<string, unknown>)
    : {};
}

export function normalizeResearchResult(raw: unknown): ResearchResult {
  if (!raw || typeof raw !== "object") {
    return {};
  }
  const r = asRecord(raw);

  const citations: Citation[] = Array.isArray(r.citations)
    ? r.citations.map((item) => {
        const c = asRecord(item);
        return {
          index: asNumber(c.index),
          source_type: c.source_type === "rag" || c.source_type === "web"
            ? c.source_type
            : undefined,
          title: asString(c.title),
          url: asNullableString(c.url),
          document_id: asNullableString(c.document_id),
          page: asNullableNumber(c.page),
          chunk_index: asNullableNumber(c.chunk_index),
        };
      })
    : [];

  const evidence: Evidence[] = Array.isArray(r.evidence)
    ? r.evidence.map((item) => {
        const e = asRecord(item);
        return {
          id: asString(e.id),
          source_type: e.source_type === "rag" || e.source_type === "web"
            ? e.source_type
            : undefined,
          text: asString(e.text),
          title: asString(e.title),
          url: asNullableString(e.url),
          document_id: asNullableString(e.document_id),
          page: asNullableNumber(e.page),
          chunk_index: asNullableNumber(e.chunk_index),
          score: asNumber(e.score),
        };
      })
    : [];

  const factChecks: FactCheck[] = Array.isArray(r.fact_checks)
    ? r.fact_checks.map((item) => {
        const f = asRecord(item);
        return {
          claim: asString(f.claim),
          verdict: asString(f.verdict),
          confidence: asNumber(f.confidence),
          evidence_refs: asStringArray(f.evidence_refs),
        };
      })
    : [];

  const criticScore =
    typeof r.critic_score === "number" ? r.critic_score : null;

  return {
    query: asString(r.query),
    report: asString(r.report) ?? asString(r.report_draft),
    report_draft: asString(r.report_draft),
    search_results: asString(r.search_results),
    sources: asStringArray(r.sources),
    citations,
    evidence,
    claims: asStringArray(r.claims),
    fact_checks: factChecks,
    confidence: asString(r.confidence),
    critic_feedback: asString(r.critic_feedback),
    critic_score: criticScore,
    errors: asStringArray(r.errors),
  };
}
