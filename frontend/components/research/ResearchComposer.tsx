"use client";

import React, { useState, useRef, useEffect } from "react";
import { ArrowRight, Sparkles, SlidersHorizontal, BookOpen, AlertCircle } from "lucide-react";

interface ResearchComposerProps {
  onSubmit: (query: string) => void;
  isLoading?: boolean;
}

export default function ResearchComposer({ onSubmit, isLoading = false }: ResearchComposerProps) {
  const [query, setQuery] = useState("");
  const [deepSearch, setDeepSearch] = useState(false);
  const [corpus, setCorpus] = useState("all");
  const [showFilters, setShowFilters] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Focus textarea on `/` keyboard press
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "/" && document.activeElement !== textareaRef.current) {
        // Prevent default browser search behavior
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

  return (
    <form onSubmit={handleSubmit} className="w-full max-w-3xl mx-auto space-y-4">
      <div className="relative group bg-card border border-border rounded-xl shadow-lg transition-all focus-within:border-primary/60 focus-within:ring-2 focus-within:ring-primary/10">
        
        {/* Input Textarea */}
        <div className="p-4">
          <textarea
            ref={textareaRef}
            rows={3}
            placeholder="Ask the research pipeline... (Press '/' to focus)"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              if (error) setError(null);
            }}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
            className="w-full bg-transparent resize-none border-0 p-0 text-foreground placeholder:text-muted-foreground focus:ring-0 focus:outline-hidden text-base leading-relaxed"
          />
        </div>

        {/* Action controls row */}
        <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-3 border-t border-border bg-muted/20 rounded-b-xl">
          <div className="flex flex-wrap items-center gap-2">
            
            {/* Corpus selector (mocked) */}
            <div className="relative">
              <select
                value={corpus}
                onChange={(e) => setCorpus(e.target.value)}
                disabled={isLoading}
                className="appearance-none bg-muted/60 hover:bg-muted border border-border hover:border-border-strong text-xs font-medium px-3 py-1.5 pr-8 rounded-lg text-muted-foreground hover:text-foreground cursor-pointer focus:outline-hidden focus:border-primary"
              >
                <option value="all">All Literature</option>
                <option value="physics">Physics & Math</option>
                <option value="biology">Biology & Medicine</option>
                <option value="cs">Computer Science</option>
              </select>
              <BookOpen size={12} className="absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none text-muted-foreground" />
            </div>

            {/* Deep Search toggle (inspired by Consensus Deep) */}
            <button
              type="button"
              onClick={() => setDeepSearch(!deepSearch)}
              disabled={isLoading}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-semibold select-none cursor-pointer transition-all duration-200
                ${deepSearch 
                  ? "border-primary bg-primary/10 text-primary" 
                  : "border-dashed border-border text-muted-foreground hover:text-foreground hover:border-border-strong"
                }`}
            >
              <Sparkles size={12} className={deepSearch ? "animate-pulse" : ""} />
              <span>Deep Engine</span>
            </button>

            {/* Filters toggle button */}
            <button
              type="button"
              onClick={() => setShowFilters(!showFilters)}
              disabled={isLoading}
              className={`flex items-center gap-1 px-3 py-1.5 rounded-lg border text-xs font-medium cursor-pointer transition-all
                ${showFilters 
                  ? "border-border-strong bg-muted text-foreground" 
                  : "border-transparent text-muted-foreground hover:text-foreground hover:bg-muted/60"
                }`}
            >
              <SlidersHorizontal size={12} />
              <span>Filters</span>
            </button>
          </div>

          {/* Submit Action */}
          <button
            type="submit"
            disabled={isLoading || !query.trim()}
            className="flex items-center justify-center h-9 w-9 rounded-lg bg-primary text-primary-foreground hover:bg-primary/95 transition-all shadow-md shadow-primary/20 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
          >
            <ArrowRight size={18} />
          </button>
        </div>
      </div>

      {/* Expanded filters panel (mocked layout) */}
      {showFilters && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 p-4 bg-card border border-border rounded-xl">
          <div>
            <label className="block text-[10px] uppercase tracking-wider font-semibold text-muted-foreground mb-1">
              Minimum Confidence Scorer
            </label>
            <select className="w-full bg-muted border border-border text-xs px-2.5 py-1.5 rounded-lg">
              <option>No filter</option>
              <option>Medium & High only</option>
              <option>High only</option>
            </select>
          </div>
          <div>
            <label className="block text-[10px] uppercase tracking-wider font-semibold text-muted-foreground mb-1">
              RAG Vector Search
            </label>
            <select className="w-full bg-muted border border-border text-xs px-2.5 py-1.5 rounded-lg">
              <option>Include Local Embeddings</option>
              <option>Exclude Local Embeddings</option>
            </select>
          </div>
        </div>
      )}

      {/* Error message */}
      {error && (
        <div className="flex items-center gap-2 text-xs text-destructive bg-destructive/5 border border-destructive/20 p-2.5 rounded-lg">
          <AlertCircle size={14} />
          <span>{error}</span>
        </div>
      )}
    </form>
  );
}
