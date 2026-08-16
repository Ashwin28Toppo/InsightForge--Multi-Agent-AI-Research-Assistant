"use client";

import { JobStatus, ResearchResult } from "../types/api";

export interface HistoryItem {
  jobId: string;
  query: string;
  status: JobStatus;
  completedAt: string;
  confidence?: string;
  reportSnippet?: string;
  duration?: string;
  resultSnapshot?: ResearchResult;
}

const HISTORY_KEY = "insightforge_research_history";

export function getHistory(): HistoryItem[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(HISTORY_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch (e) {
    console.error("Failed to read localStorage history:", e);
    return [];
  }
}

export function saveHistoryItem(item: Omit<HistoryItem, "completedAt">): void {
  if (typeof window === "undefined") return;
  try {
    const history = getHistory();
    const existingIdx = history.findIndex((h) => h.jobId === item.jobId);
    
    const newItem: HistoryItem = {
      ...item,
      completedAt: new Date().toLocaleDateString(),
    };

    if (existingIdx >= 0) {
      history[existingIdx] = newItem;
    } else {
      history.unshift(newItem);
    }

    localStorage.setItem(HISTORY_KEY, JSON.stringify(history));
  } catch (e) {
    console.error("Failed to write localStorage history item:", e);
  }
}

export function deleteHistoryItem(jobId: string): void {
  if (typeof window === "undefined") return;
  try {
    const history = getHistory();
    const filtered = history.filter((h) => h.jobId !== jobId);
    localStorage.setItem(HISTORY_KEY, JSON.stringify(filtered));
  } catch (e) {
    console.error("Failed to delete localStorage history item:", e);
  }
}
