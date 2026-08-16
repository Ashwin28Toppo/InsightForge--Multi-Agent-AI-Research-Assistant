"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Plus,
  History,
  Menu,
  X,
  LayoutGrid,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import BottomTabBar from "./BottomTabBar";

interface AppShellProps {
  children: React.ReactNode;
  healthStatus?: "online" | "offline" | "checking";
}

export default function AppShell({ children, healthStatus = "online" }: AppShellProps) {
  const pathname = usePathname();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

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
      {/* Mobile Sidebar overlay */}
      {sidebarOpen && (
        <div 
          className="fixed inset-0 z-40 bg-black/60 backdrop-blur-xs lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar Container */}
      <aside 
        className={`fixed inset-y-0 left-0 z-50 flex flex-col bg-sidebar border-r border-sidebar-border transition-all duration-300
          lg:static lg:translate-x-0
          ${sidebarOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"}
          ${sidebarCollapsed ? "w-16" : "w-64"}`}
      >
        {/* Sidebar Header */}
        <div className="h-16 flex items-center justify-between px-4 border-b border-sidebar-border">
          <Link href="/" className="flex items-center gap-2 font-syne select-none">
            <div className="h-8 w-8 rounded-lg bg-primary flex items-center justify-center text-primary-foreground font-bold shadow-md shadow-primary/20">
              IF
            </div>
            {!sidebarCollapsed && (
              <span className="font-bold text-lg tracking-tight bg-gradient-to-r from-foreground to-muted-foreground bg-clip-text text-transparent">
                InsightForge
              </span>
            )}
          </Link>
          <button 
            className="lg:hidden text-muted-foreground hover:text-foreground"
            onClick={() => setSidebarOpen(false)}
          >
            <X size={20} />
          </button>
        </div>

        {/* Navigation Items */}
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

        {/* Sidebar Footer */}
        <div className="p-3 border-t border-sidebar-border space-y-2 bg-sidebar">
          {/* Collapse toggle (desktop only) */}
          <button
            onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
            className="hidden lg:flex items-center gap-3 w-full px-3 py-2 rounded-lg text-xs font-semibold text-muted-foreground hover:bg-muted hover:text-foreground transition-all uppercase tracking-wider"
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

          {/* User profile (mock) */}
          <div className="flex items-center gap-3 px-2 py-1.5 rounded-lg bg-muted/30">
            <div className="h-8 w-8 rounded-full bg-slate-800 border border-border-strong flex items-center justify-center font-bold text-xs select-none">
              R
            </div>
            {!sidebarCollapsed && (
              <div className="flex-1 min-w-0">
                <p className="text-xs font-semibold truncate">Researcher</p>
                <p className="text-[10px] text-muted-foreground truncate">workspace_active</p>
              </div>
            )}
          </div>
        </div>
      </aside>

      {/* Main App Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top Header */}
        <header className="h-16 flex items-center justify-between px-6 border-b border-border bg-background/50 backdrop-blur-md">
          <div className="flex items-center gap-4">
            <button
              onClick={() => setSidebarOpen(true)}
              className="lg:hidden p-1 rounded-md text-muted-foreground hover:bg-muted hover:text-foreground"
            >
              <Menu size={20} />
            </button>
            <div className="hidden sm:flex items-center gap-2 text-xs font-semibold text-muted-foreground uppercase tracking-widest font-mono">
              <LayoutGrid size={14} />
              <span>Multi-Agent Research Terminal</span>
            </div>
          </div>

          {/* Header Action / Health Badge */}
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full border border-border bg-card text-xs font-medium">
              <span className={`h-2 w-2 rounded-full relative flex`}>
                <span className={`absolute inline-flex h-full w-full rounded-full opacity-75 ${
                  healthStatus === "online" ? "animate-ping bg-success" : healthStatus === "checking" ? "animate-ping bg-warning" : "bg-destructive"
                }`}></span>
                <span className={`relative inline-flex rounded-full h-2 w-2 ${
                  healthStatus === "online" ? "bg-success" : healthStatus === "checking" ? "bg-warning" : "bg-destructive"
                }`}></span>
              </span>
              <span className="font-mono text-[10px] uppercase text-muted-foreground select-none">
                Service: {healthStatus}
              </span>
            </div>
          </div>
        </header>

        {/* Content Area */}
        <main className="flex-1 overflow-y-auto relative flex flex-col pb-16 lg:pb-0">
          {children}
        </main>
      </div>

      {/* Mobile bottom navigation */}
      <BottomTabBar />
    </div>
  );
}
