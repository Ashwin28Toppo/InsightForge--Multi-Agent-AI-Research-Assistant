"use client";

import React from "react";
import Skeleton from "@/components/feedback/Skeleton";
import SignInPrompt from "./SignInPrompt";
import { useAuth } from "@/lib/auth/auth-context";

interface AuthGateProps {
  children: React.ReactNode;
  promptTitle?: string;
  promptBody?: string;
}

export default function AuthGate({
  children,
  promptTitle,
  promptBody,
}: AuthGateProps) {
  const { status } = useAuth();

  if (status === "checking") {
    return (
      <div
        className="w-full max-w-3xl mx-auto px-6 py-10"
        aria-busy="true"
        aria-label="Checking session"
      >
        <div className="bg-card border border-border rounded-xl p-6">
          <Skeleton lines={2} />
        </div>
      </div>
    );
  }

  if (status === "unauthenticated") {
    return <SignInPrompt title={promptTitle} body={promptBody} />;
  }

  return <>{children}</>;
}
