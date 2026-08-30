"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Plus, History } from "lucide-react";

/** Mobile bottom navigation (visible < lg). */
export default function BottomTabBar() {
  const pathname = usePathname();

  const items = [
    { name: "New Research", href: "/", icon: Plus, active: pathname === "/" },
    {
      name: "History",
      href: "/history",
      icon: History,
      active: pathname.startsWith("/history"),
    },
  ];

  return (
    <nav
      className="lg:hidden fixed bottom-0 inset-x-0 z-40 border-t border-sidebar-border bg-sidebar/95 backdrop-blur-md"
      aria-label="Primary mobile navigation"
    >
      <div className="grid grid-cols-2">
        {items.map((item) => {
          const Icon = item.icon;
          return (
            <Link
              key={item.name}
              href={item.href}
              className={`flex flex-col items-center justify-center gap-1 py-2.5 text-[10px] font-mono font-bold uppercase tracking-wider transition-colors
                ${item.active ? "text-primary" : "text-muted-foreground hover:text-foreground"}`}
            >
              <Icon size={18} />
              <span>{item.name}</span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
