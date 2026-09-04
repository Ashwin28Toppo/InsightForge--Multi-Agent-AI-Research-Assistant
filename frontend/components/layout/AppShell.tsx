"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  Plus,
  History,
  Menu,
  X,
  LayoutGrid,
  ChevronLeft,
  ChevronRight,
  LogIn,
  LogOut,
} from "lucide-react";
import BottomTabBar from "./BottomTabBar";
import { useHealth } from "@/hooks/useHealth";
import { useAuth } from "@/lib/auth/auth-context";

interface AppShellProps {
  children: React.ReactNode;
  healthStatus?: "online" | "offline" | "checking";
}

const HEALTH_LABELS: Record<string, string> = {
  online: "Connected",
  checking: "Checking",
  offline: "Unavailable",
};

export default function AppShell({ children, healthStatus }: AppShellProps) {
  const pathname = usePathname();
  const router = useRouter();
  const { healthStatus: liveHealth } = useHealth();
  const { user, status: authStatus, logout } = useAuth();
  const status = healthStatus ?? liveHealth;
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  const userInitial =
    user?.name?.trim()?.charAt(0).toUpperCase() ||
    user?.email?.charAt(0).toUpperCase() ||
    "?";
  const displayName = user?.name?.trim() || user?.email || "";

  const handleLogout = async () => {
    try {
      await logout();
    } finally {
      router.push("/");
    }
  };

  const navItems = [
    { name: "New Research", href: "/", icon: Plus, matchExact: true },
    { name: "Research History", href: "/history", icon: History, matchExact: false },
  ];

  const isLinkActive = (item: typeof navItems[0]) => {
    if (item.matchExact) {
      return pathname === item.href;
    }
    return pathname.startsWith(item.href);
  };

  return (
    <div className="flex h-screen overflow-hidden bg-background text-foreground">
      {sidebarOpen && (
            <div
        />
      )}

      <aside 
        className={`fixed inset-y-0 left-0 z-50 flex flex-col bg-sidebar border-r border-sidebar-border transition-all duration-300
          lg:static lg:translate-x-0
          ${sidebarOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"}
          ${sidebarCollapsed ? "w-16" : "w-64"}`}
      >
        <div className="h-16 flex items-center justify-between px-4 border-b border-sidebar-border">
          <Link href="/" className="flex items-center gap-2 font-syne select-none">
            <div className="h-8 w-8 rounded-lg bg-primary flex items-center justify-center text-primary-foreground font-bold shadow-md shadow-primary/20">
              IF
            </div>
            {!sidebarCollapsed && (
              <span className="font-bold text-lg tracking-tight bg-linear-to-r from-foreground to-muted-foreground bg-clip-text text-transparent">
                InsightForge
              </span>
            )}
          </Link>
          <button
            className="lg:hidden text-muted-foreground hover:text-foreground cursor-pointer"
            onClick={() => setSidebarOpen(false)}
            aria-label="Close navigation menu"
          >
            <X size={20} />
          </button>
        </div>

        <nav className="flex-1 px-3 py-4 space-y-1.5 overflow-y-auto">
          {navItems.map((item) => {
            const active = isLinkActive(item);
            const Icon = item.icon;
            return (
              <Link
                key={item.name}
                href={item.href}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg font-medium text-sm transition-all group
                  ${active 
                    ? "bg-primary text-primary-foreground font-semibold shadow-md shadow-primary/10" 
                    : "text-muted-foreground hover:bg-muted hover:text-foreground"
                  }`}
                onClick={() => setSidebarOpen(false)}
                title={sidebarCollapsed ? item.name : undefined}
              >
                <Icon size={18} className={active ? "" : "text-muted-foreground group-hover:text-foreground"} />
                {!sidebarCollapsed && <span>{item.name}</span>}
              </Link>
            );
          })}
        </nav>

        <div className="p-3 border-t border-sidebar-border space-y-2 bg-sidebar">
          <button
            onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
            aria-pressed={sidebarCollapsed}
            className="hidden lg:flex items-center gap-3 w-full px-3 py-2 rounded-lg text-xs font-semibold text-muted-foreground hover:bg-muted hover:text-foreground transition-all uppercase tracking-wider cursor-pointer"
          >
            {sidebarCollapsed ? (
              <>
                <ChevronRight size={16} />
              </>
            ) : (
              <>
                <ChevronLeft size={16} />
                <span>Collapse Sidebar</span>
              </>
            )}
          </button>

          <div className="px-2 py-1.5 rounded-lg bg-muted/30 space-y-1.5">
            {authStatus === "authenticated" && user ? (
              <>
                <div className="flex items-center gap-3">
                  <div className="h-8 w-8 rounded-full bg-primary/90 border border-primary/30 flex items-center justify-center font-bold text-xs select-none text-primary-foreground">
                    {userInitial}
                  </div>
                  {!sidebarCollapsed && (
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-semibold truncate">
                        {displayName}
                      </p>
                      <p className="text-[10px] text-muted-foreground truncate">
                        {user.email}
                      </p>
                    </div>
                  )}
                </div>
                {!sidebarCollapsed && (
                  <button
                    type="button"
                    onClick={handleLogout}
                    className="flex items-center gap-1.5 w-full px-2 py-1.5 rounded-lg text-[10px] font-mono font-bold uppercase tracking-wider text-muted-foreground hover:text-destructive hover:bg-destructive/5 transition-all cursor-pointer"
                  >
                    <LogOut size={12} />
                    <span>Sign out</span>
                  </button>
                )}
              </>
            ) : authStatus === "checking" ? (
              <p className="text-[10px] font-mono text-muted-foreground text-center py-2 animate-pulse select-none">
                Checking session…
              </p>
            ) : (
              <Link
                href="/auth"
                className="flex items-center gap-1.5 w-full px-2 py-1.5 rounded-lg text-[10px] font-mono font-bold uppercase tracking-wider text-muted-foreground hover:text-primary hover:bg-muted transition-all cursor-pointer"
              >
                <LogIn size={12} />
                {!sidebarCollapsed && <span>Sign in</span>}
              </Link>
            )}
          </div>
        </div>
      </aside>

      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <header className="h-16 flex items-center justify-between px-6 border-b border-border bg-background/50 backdrop-blur-md">
          <div className="flex items-center gap-4">
            <button
              onClick={() => setSidebarOpen(true)}
              className="lg:hidden p-1 rounded-md text-muted-foreground hover:bg-muted hover:text-foreground cursor-pointer"
              aria-label="Open navigation menu"
            >
              <Menu size={20} />
            </button>
            <div className="hidden sm:flex items-center gap-2 text-xs font-semibold text-muted-foreground uppercase tracking-widest font-mono">
              <LayoutGrid size={14} />
              <span>Multi-Agent Research Terminal</span>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <div
              className="flex items-center gap-2 px-3 py-1.5 rounded-full border border-border bg-card text-xs font-medium"
              title={status === "offline" ? "Backend unreachable — research submissions will fail" : undefined}
            >
              <span className="h-2 w-2 rounded-full relative flex">
                <span
                  className={`absolute inline-flex h-full w-full rounded-full opacity-75 ${
                    status === "online"
                      ? "animate-ping bg-success motion-reduce:animate-none"
                      : status === "checking"
                        ? "animate-ping bg-info motion-reduce:animate-none"
                        : "bg-destructive"
                  }`}
                />
                <span
                  className={`relative inline-flex rounded-full h-2 w-2 ${
                    status === "online"
                      ? "bg-success"
                      : status === "checking"
                        ? "bg-info"
                        : "bg-destructive"
                  }`}
                />
              </span>
              <span className="font-mono text-[10px] uppercase text-muted-foreground select-none">
                Service: {HEALTH_LABELS[status] ?? status}
              </span>
            </div>
          </div>
        </header>

        <main className="flex-1 overflow-y-auto relative flex flex-col pb-16 lg:pb-0">
          {children}
        </main>
      </div>

      <BottomTabBar />
    </div>
  );
}
