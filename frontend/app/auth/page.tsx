"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import AppShell from "@/components/layout/AppShell";
import { useAuth } from "@/lib/auth/auth-context";
import { apiErrorMessage } from "@/lib/utils/errors";
import { ApiError } from "@/lib/api/client";
import { Loader2, Lock, LogIn, Mail, UserPlus, Eye, EyeOff } from "lucide-react";

type Mode = "login" | "signup";

/** Auth-specific error copy (kept local so shared research errors stay generic). */
function authErrorMessage(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.status === 401) {
      return "Invalid email or password.";
    }
    if (err.status === 409) {
      return "That email is already registered — try signing in instead.";
    }
    if (err.status === 422) {
      return "Please check your email and password.";
    }
  }
  return apiErrorMessage(err);
}

const INPUT_CLASSES =
  "w-full bg-card border border-border focus:border-primary/60 focus:ring-2 focus:ring-primary/10 pl-10 pr-4 py-2.5 rounded-xl text-sm text-foreground placeholder:text-muted-foreground focus:outline-none transition-all";

export default function AuthPage() {
  const router = useRouter();
  const { status, user, login, signup } = useAuth();
  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // Already authenticated — nothing to do on the auth page.
  if (status === "authenticated" && user) {
    return (
      <AppShell>
        <div className="flex-1 flex items-center justify-center px-6 py-12">
          <div className="max-w-md w-full bg-card border border-border rounded-xl p-8 text-center space-y-4">
            <div className="h-12 w-12 rounded-full bg-success/10 border border-success/25 flex items-center justify-center text-success mx-auto">
              <Lock size={22} />
            </div>
            <div className="space-y-1.5">
              <h2 className="text-base font-bold font-syne text-foreground">
                Already signed in
              </h2>
              <p className="text-xs text-muted-foreground leading-relaxed">
                You are authenticated as{" "}
                <span className="font-mono text-foreground">{user.email}</span>
                .
              </p>
            </div>
            <div className="pt-2">
              <button
                type="button"
                onClick={() => router.push("/")}
                className="inline-flex px-4 py-2 bg-primary text-primary-foreground font-semibold text-xs rounded-lg hover:bg-primary/95 cursor-pointer transition-all shadow-md shadow-primary/10"
              >
                Back to workspace
              </button>
            </div>
          </div>
        </div>
      </AppShell>
    );
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const cleanEmail = email.trim().toLowerCase();
    if (!cleanEmail || !password) {
      setError("Email and password are required.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      if (mode === "signup") {
        await signup({
          email: cleanEmail,
          password,
          name: name.trim() || null,
        });
      } else {
        await login(cleanEmail, password);
      }
      router.push("/");
    } catch (err) {
      setError(authErrorMessage(err));
      setSubmitting(false);
    }
  };

  return (
    <AppShell>
      <div className="flex-1 flex items-center justify-center px-6 py-12">
        <div className="w-full max-w-md space-y-6">
          {/* Header */}
          <div className="space-y-1.5 text-center">
            <p className="text-xs font-mono font-bold uppercase tracking-widest text-primary select-none">
              InsightForge Access
            </p>
            <h1 className="text-xl md:text-2xl font-bold font-syne tracking-tight text-foreground">
              {mode === "login" ? "Sign in to your workspace" : "Create your account"}
            </h1>
            <p className="text-xs text-muted-foreground leading-relaxed">
              Authentication is handled by secure HttpOnly cookies — your
              session never touches browser storage.
            </p>
          </div>

          {/* Mode tabs */}
          <div
            className="flex items-center gap-1 p-1 rounded-xl bg-card border border-border"
            role="tablist"
            aria-label="Authentication mode"
          >
            {(
              [
                { key: "login", label: "Sign in", icon: LogIn },
                { key: "signup", label: "Create account", icon: UserPlus },
              ] as { key: Mode; label: string; icon: React.ComponentType<{ size?: number | string }> }[]
            ).map((option) => {
              const Icon = option.icon;
              return (
                <button
                  key={option.key}
                  type="button"
                  role="tab"
                  aria-selected={mode === option.key}
                  onClick={() => {
                    setMode(option.key);
                    setError(null);
                  }}
                  className={`flex-1 inline-flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg text-xs font-mono font-bold uppercase tracking-wider cursor-pointer transition-all
                    ${
                      mode === option.key
                        ? "bg-primary text-primary-foreground"
                        : "text-muted-foreground hover:text-foreground"
                    }`}
                >
                  <Icon size={13} />
                  <span>{option.label}</span>
                </button>
              );
            })}
          </div>

          {/* Form */}
          <form
            onSubmit={handleSubmit}
            className="bg-card border border-border rounded-xl p-6 space-y-4"
          >
            {mode === "signup" && (
              <div className="space-y-1.5">
                <label
                  htmlFor="auth-name"
                  className="text-[10px] font-mono font-bold uppercase tracking-widest text-muted-foreground"
                >
                  Name <span className="normal-case font-normal">(optional)</span>
                </label>
                <div className="relative">
                  <Mail
                    size={15}
                    className="absolute left-3.5 top-1/2 -translate-y-1/2 text-muted-foreground pointer-events-none"
                  />
                  <input
                    id="auth-name"
                    type="text"
                    autoComplete="name"
                    placeholder="Ada Lovelace"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className={INPUT_CLASSES}
                  />
                </div>
              </div>
            )}

            <div className="space-y-1.5">
              <label
                htmlFor="auth-email"
                className="text-[10px] font-mono font-bold uppercase tracking-widest text-muted-foreground"
              >
                Email
              </label>
              <div className="relative">
                <Mail
                  size={15}
                  className="absolute left-3.5 top-1/2 -translate-y-1/2 text-muted-foreground pointer-events-none"
                />
                <input
                  id="auth-email"
                  type="email"
                  required
                  autoComplete="email"
                  placeholder="you@example.com"
                  value={email}
                  onChange={(e) => {
                    setEmail(e.target.value);
                    if (error) setError(null);
                  }}
                  className={INPUT_CLASSES}
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <label
                htmlFor="auth-password"
                className="text-[10px] font-mono font-bold uppercase tracking-widest text-muted-foreground"
              >
                Password
              </label>
              <div className="relative">
                <Lock
                  size={15}
                  className="absolute left-3.5 top-1/2 -translate-y-1/2 text-muted-foreground pointer-events-none"
                />
                <input
                  id="auth-password"
                  type={showPassword ? "text" : "password"}
                  required
                  autoComplete={
                    mode === "signup" ? "new-password" : "current-password"
                  }
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => {
                    setPassword(e.target.value);
                    if (error) setError(null);
                  }}
                  className={INPUT_CLASSES}
                />
                <button
                  type="button"
                  aria-label={showPassword ? "Hide password" : "Show password"}
                  onClick={() => setShowPassword((s) => !s)}
                  className="absolute right-3.5 top-1/2 -translate-y-1/2 text-muted-foreground"
                >
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            {error && (
              <div
                role="alert"
                className="flex items-start gap-2 text-xs text-destructive bg-destructive/5 border border-destructive/20 p-2.5 rounded-lg"
              >
                <Lock size={13} className="mt-0.5 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <button
              type="submit"
              disabled={submitting || status === "checking"}
              className="w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 bg-primary text-primary-foreground font-semibold text-xs rounded-lg hover:bg-primary/95 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer transition-all shadow-md shadow-primary/10"
            >
              {submitting ? (
                <Loader2 size={14} className="animate-spin motion-reduce:animate-none" />
              ) : mode === "login" ? (
                <LogIn size={14} />
              ) : (
                <UserPlus size={14} />
              )}
              <span>
                {submitting
                  ? "Please wait…"
                  : mode === "login"
                    ? "Sign in"
                    : "Create account"}
              </span>
            </button>
          </form>

          <p className="text-[10px] font-mono text-muted-foreground text-center leading-relaxed">
            Sessions use HttpOnly cookies only — no tokens in localStorage or
            sessionStorage.
          </p>
        </div>
      </div>
    </AppShell>
  );
}
