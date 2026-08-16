"use client";

import React, { useState, useRef, useEffect } from "react";
import { ArrowRight, Loader2, AlertCircle } from "lucide-react";

interface ResearchComposerProps {
  onSubmit: (query: string) => void;
  isLoading?: boolean;
  /** Server/API-level error to display inside the composer (e.g. 422, offline). */
  externalError?: string | null;
}

export default function ResearchComposer({
  onSubmit,
  isLoading = false,
  externalError = null,
}: ResearchComposerProps) {
  const [query, setQuery] = useState("");
  const [error, setError] = useState<string | null>(null);

  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Focus textarea on `/` keyboard press.
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "/" && document.activeElement !== textareaRef.current) {
        // Prevent default browser quick-find behavior.
        e.preventDefault();
        textareaRef.current?.focus();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const cleanQuery = query.trim();
    if (!cleanQuery) {
      setError("Please enter a research query");
      return;
    }
    setError(null);
    onSubmit(cleanQuery);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const canSubmit = query.trim().length > 0 && !isLoading;

  return (
    <form onSubmit={handleSubmit} className="w-full">
      <div className="bg-card border border-border rounded-xl shadow-sm transition-all focus-within:border-primary/50 focus-within:ring-2 focus-within:ring-primary/15">
        <textarea
          ref={textareaRef}
          rows={4}
          placeholder="Describe the subject you want investigated — e.g. “What is the current evidence for intermittent fasting?”"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            if (error) setError(null);
          }}
          onKeyDown={handleKeyDown}
          disabled={isLoading}
          aria-label="Research query"
          className="w-full bg-transparent resize-y border-0 p-4 md:p-5 text-foreground placeholder:text-muted-foreground focus:outline-hidden focus:ring-0 text-[15px] leading-relaxed"
        />

        {/* Action row — submission is the only control; no fake toggles. */}
        <div className="flex flex-wrap items-center justify-between gap-3 px-4 md:px-5 py-3 border-t border-border bg-muted/20 rounded-b-xl">
          <p className="text-[10px] font-mono text-muted-foreground select-none">
            <kbd className="px-1 py-0.5 rounded bg-muted border border-border">↵</kbd> run
            <span className="mx-1.5 text-border-strong">·</span>
            <kbd className="px-1 py-0.5 rounded bg-muted border border-border">Shift+↵</kbd> newline
            <span className="mx-1.5 text-border-strong">·</span>
            <kbd className="px-1 py-0.5 rounded bg-muted border border-border">/</kbd> focus
          </p>

          <button
            type="submit"
            disabled={!canSubmit}
            className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground font-semibold text-xs rounded-lg hover:bg-primary/95 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer transition-all"
          >
            {isLoading ? (
              <Loader2 size={14} className="animate-spin motion-reduce:animate-none" />
            ) : (
              <ArrowRight size={14} />
            )}
            <span>{isLoading ? "Submitting…" : "Initiate Research"}</span>
          </button>
        </div>
      </div>

      {/* Error message — local validation or server/API error */}
      {(error || externalError) && (
        <div
          role="alert"
          className="flex items-start gap-2 text-xs text-destructive bg-destructive/5 border border-destructive/20 p-2.5 rounded-lg mt-3"
        >
          <AlertCircle size={14} className="mt-0.5 shrink-0" />
          <span>{error || externalError}</span>
        </div>
      )}
    </form>
  );
}
