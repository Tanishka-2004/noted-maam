"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { 
  Home, 
  Video, 
  CheckSquare, 
  Activity, 
  BookOpen, 
  Settings, 
  Sparkles,
  Plus
} from "lucide-react";

export function Navigation() {
  const pathname = usePathname();

  const navItems = [
    { label: "Home", path: "/app/home", icon: Home },
    { label: "Meetings", path: "/app/meetings", icon: Video, badge: "1 Inbox" },
    { label: "Work", path: "/app/work", icon: CheckSquare, badge: "2 Verify" },
    { label: "Projects", path: "/app/projects", icon: Activity },
    { label: "Knowledge", path: "/app/knowledge", icon: BookOpen },
    { label: "Settings", path: "/app/settings", icon: Settings },
  ];

  return (
    <header className="sticky top-0 z-40 w-full border-b border-[#CDBEA9] bg-[#FBF8F1]/90 backdrop-blur-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        
        {/* Brand Logo & Thesis */}
        <div className="flex items-center gap-6">
          <Link href="/app/home" className="flex items-center gap-3 group">
            <div className="w-9 h-9 rounded-xl bg-[#681F32] p-0.5 shadow-md group-hover:scale-105 transition-transform flex items-center justify-center text-[#FBF8F1]">
              <Sparkles className="w-5 h-5 text-[#FBF8F1]" />
            </div>
            <div>
              <span className="font-bold text-base tracking-tight text-[#4A1724] flex items-center gap-1.5 font-display">
                Noted Ma'am
                <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-[#681F32]/10 text-[#681F32] border border-[#681F32]/20 font-bold">Burgundy & Cream</span>
              </span>
              <span className="text-[11px] text-[#96546A] block -mt-0.5 font-medium">Meetings End. Work Begins.</span>
            </div>
          </Link>
        </div>

        {/* 5 Primary Job Navigation Links */}
        <nav className="hidden md:flex items-center gap-1.5">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.path || (item.path !== "/" && pathname?.startsWith(item.path));
            return (
              <Link
                key={item.path}
                href={item.path}
                className={`px-3.5 py-2 rounded-xl text-xs font-semibold transition-all flex items-center gap-2 ${
                  isActive 
                    ? "bg-[#681F32] text-[#FBF8F1] shadow-md" 
                    : "text-[#4A1724] hover:text-[#681F32] hover:bg-[#E9DFCE]"
                }`}
              >
                <Icon className={`w-4 h-4 ${isActive ? "text-[#FBF8F1]" : "text-[#96546A]"}`} />
                <span>{item.label}</span>
                {item.badge && (
                  <span className={`text-[10px] font-mono font-bold px-1.5 py-0.2 rounded-full ${
                    isActive 
                      ? "bg-[#FBF8F1] text-[#681F32]" 
                      : "bg-[#E9DFCE] text-[#4A1724] border border-[#CDBEA9]"
                  }`}>
                    {item.badge}
                  </span>
                )}
              </Link>
            );
          })}
        </nav>

        {/* Ingestion & Action CTA */}
        <div className="flex items-center gap-3">
          <Link
            href="/onboarding"
            className="px-3.5 py-2 rounded-xl bg-[#681F32] hover:bg-[#4A1724] text-[#FBF8F1] text-xs font-semibold transition-all flex items-center gap-1.5 shadow-md"
          >
            <Plus className="w-3.5 h-3.5 text-[#FBF8F1]" />
            <span>Upload Meeting</span>
          </Link>
        </div>
      </div>

      {/* Mobile Sub-Navigation Bar */}
      <div className="md:hidden flex overflow-x-auto gap-2 px-4 py-2 border-t border-[#CDBEA9] bg-[#FBF8F1] no-scrollbar">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.path;
          return (
            <Link
              key={item.path}
              href={item.path}
              className={`shrink-0 px-3 py-1.5 rounded-lg text-xs font-medium flex items-center gap-1.5 ${
                isActive 
                  ? "bg-[#681F32] text-[#FBF8F1]" 
                  : "text-[#4A1724] bg-[#E9DFCE]"
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              <span>{item.label}</span>
            </Link>
          );
        })}
      </div>
    </header>
  );
}
