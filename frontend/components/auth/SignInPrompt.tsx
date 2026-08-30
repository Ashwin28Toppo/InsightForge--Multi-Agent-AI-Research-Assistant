"use client";

import React from "react";
import Link from "next/link";
import { Lock } from "lucide-react";

interface SignInPromptProps {
  title?: string;
  body?: string;
}

/**
 * Centered sign-in prompt for authenticated surfaces. Rendered by pages when
 * there is no session; the backend remains the authority (it 401s without a
 * valid cookie). Never exposes any user data.
 */
export default function SignInPrompt({
  title = "Sign in required",
  body = "This workspace is authenticated. Sign in to start research and access your research history.",
}: SignInPromptProps) {
  return (
    <div className="w-full max-w-md mx-auto py-12 px-6">
      <div className="bg-card border border-border rounded-xl p-8 text-center space-y-4">
        <div className="h-12 w-12 rounded-full bg-muted border border-border flex items-center justify-center text-muted-foreground mx-auto">
          <Lock size={22} />
        </div>
        <div className="space-y-1.5">
          <h2 className="text-base font-bold font-syne text-foreground">
            {title}
          </h2>
          <p className="text-xs text-muted-foreground leading-relaxed max-w-sm mx-auto">
            {body}
          </p>
        </div>
        <div className="pt-2">
          <Link
            href="/auth"
            className="inline-flex px-4 py-2 bg-primary text-primary-foreground font-semibold text-xs rounded-lg hover:bg-primary/95 cursor-pointer transition-all shadow-md shadow-primary/10"
          >
            Sign in / Create account
          </Link>
        </div>
      </div>
    </div>
  );
}
