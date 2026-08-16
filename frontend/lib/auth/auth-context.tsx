"use client";

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import {
  getCurrentUser,
  login as apiLogin,
  logout as apiLogout,
  signup as apiSignup,
} from "@/lib/api/auth";
import type { AuthRequest, UserResponse } from "@/lib/types/api";

export type AuthStatus = "checking" | "authenticated" | "unauthenticated";

interface AuthContextValue {
  /** Session resolution state: "checking" while /auth/me is in flight. */
  status: AuthStatus;
  /** The authenticated user, or null when not authenticated. */
  user: UserResponse | null;
  login: (email: string, password: string) => Promise<UserResponse>;
  signup: (payload: AuthRequest) => Promise<UserResponse>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

/**
 * Session provider (Phase 2F Step 7).
 *
 * On app startup it calls ``GET /auth/me`` to resolve the current session.
 * The JWT lives ONLY in the backend's HttpOnly cookie — this module never
 * stores tokens in localStorage, sessionStorage, or component state. The
 * backend remains the sole authority: the UI only reflects what /auth/me
 * reports, and every research/history call still authenticates server-side.
 */
export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>("checking");
  const [user, setUser] = useState<UserResponse | null>(null);

  useEffect(() => {
    let cancelled = false;
    getCurrentUser()
      .then((current) => {
        if (cancelled) return;
        setUser(current);
        setStatus("authenticated");
      })
      .catch(() => {
        // 401 (no session) and network failures alike resolve to
        // "unauthenticated" — the UI must never block forever.
        if (cancelled) return;
        setUser(null);
        setStatus("unauthenticated");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const current = await apiLogin({ email, password });
    setUser(current);
    setStatus("authenticated");
    return current;
  }, []);

  const signup = useCallback(async (payload: AuthRequest) => {
    const current = await apiSignup(payload);
    setUser(current);
    setStatus("authenticated");
    return current;
  }, []);

  const logout = useCallback(async () => {
    try {
      await apiLogout();
    } finally {
      // Clear local UI state regardless of network outcome — the cookie is
      // stateless and will be rejected server-side anyway.
      setUser(null);
      setStatus("unauthenticated");
    }
  }, []);

  const value = useMemo(
    () => ({ status, user, login, signup, logout }),
    [status, user, login, signup, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return ctx;
}
