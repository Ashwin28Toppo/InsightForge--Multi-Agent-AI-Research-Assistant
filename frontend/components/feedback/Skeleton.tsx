"use client";

import React from "react";

interface SkeletonProps {
  className?: string;
  lines?: number;
}

/** Shimmer placeholder that mirrors the final layout shape. */
export default function Skeleton({ className = "", lines = 3 }: SkeletonProps) {
  return (
    <div className={`animate-pulse space-y-3 ${className}`} aria-hidden="true">
      <div className="h-6 bg-border rounded-md w-1/3" />
      {Array.from({ length: lines }).map((_, i) => (
        <div
          key={i}
          className={`h-4 bg-border rounded-md ${
            i % 3 === 0 ? "w-full" : i % 3 === 1 ? "w-11/12" : "w-8/12"
          }`}
        />
      ))}
    </div>
  );
}
