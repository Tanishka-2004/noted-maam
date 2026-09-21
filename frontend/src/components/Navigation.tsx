"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAppMode } from "../context/AppModeContext";
import { 
  Home, 
  Video, 
  CheckSquare, 
  Activity, 
  BookOpen, 
  Settings, 
  Sparkles,
  Plus,
  ArrowRightLeft
} from "lucide-react";

export function Navigation() {
  const pathname = usePathname();
  const { mode, toggleMode } = useAppMode();

  const navItems = [
    { label: "Home", path: "/app/home", icon: Home },
    { label: "Meetings", path: "/app/meetings", icon: Video, badge: "1 Inbox" },
    { label: "Work", path: "/app/work", icon: CheckSquare, badge: "2 Verify" },
    { label: "Projects", path: "/app/projects", icon: Activity },
    { label: "Knowledge", path: "/app/knowledge", icon: BookOpen },
    { label: "Settings", path: "/app/settings", icon: Settings },
  ];

  return (
    <header className="sticky top-0 z-40 w-full border-b border-[#681F32] bg-[#4A1724]/95 backdrop-blur-md text-[#FBF8F1]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        
        {/* Brand Logo */}
        <div className="flex items-center gap-6">
          <Link href="/app/home" className="flex items-center gap-3 group">
            <div className="w-9 h-9 rounded-xl bg-[#FBF8F1] p-0.5 shadow-md group-hover:scale-105 transition-transform flex items-center justify-center text-[#4A1724]">
              <Sparkles className="w-5 h-5 text-[#4A1724]" />
            </div>
            <div>
              <span className="font-bold text-base tracking-tight text-[#FBF8F1] flex items-center gap-2 font-sans">
                Noted Ma'am
              </span>
              <span className="text-[11px] text-[#E9DFCE] block -mt-0.5 font-medium">Meetings End. Work Begins.</span>
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
                    ? "bg-[#FBF8F1] text-[#4A1724] shadow-sm font-bold" 
                    : "text-[#E9DFCE] hover:text-[#FBF8F1] hover:bg-[#681F32]/60"
                }`}
              >
                <Icon className={`w-4 h-4 ${isActive ? "text-[#4A1724]" : "text-[#CDBEA9]"}`} />
                <span>{item.label}</span>
                {item.badge && (
                  <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full ${
                    isActive 
                      ? "bg-[#4A1724] text-[#FBF8F1]" 
                      : "bg-[#681F32] text-[#FBF8F1] border border-[#7A2940]"
                  }`}>
                    {item.badge}
                  </span>
                )}
              </Link>
            );
          })}
        </nav>

        {/* Right Action Group: Mode Toggle & Upload Meeting */}
        <div className="flex items-center gap-2.5">
          {/* Mode Switcher */}
          <button
            onClick={toggleMode}
            title={mode === "DEMO" ? "Switch to Real Production Mode" : "Switch to Demo Mode"}
            className="px-3 py-1.5 rounded-xl text-xs font-semibold flex items-center gap-2 transition-all border border-[#7A2940] bg-[#681F32] text-[#FBF8F1] hover:bg-[#7A2940] shadow-xs"
          >
            <span className={`w-2 h-2 rounded-full ${mode === "DEMO" ? "bg-[#FBF8F1]" : "bg-emerald-400 animate-pulse"}`} />
            <span>{mode === "DEMO" ? "Demo Mode" : "Real Mode"}</span>
            <ArrowRightLeft className="w-3 h-3 text-[#E9DFCE]" />
          </button>

          {/* Upload Meeting Button */}
          <Link
            href="/onboarding"
            className="px-3.5 py-1.5 rounded-xl bg-[#FBF8F1] hover:bg-[#F7F1E5] text-[#4A1724] text-xs font-bold transition-all flex items-center gap-1.5 shadow-sm"
          >
            <Plus className="w-3.5 h-3.5 text-[#4A1724]" />
            <span>Upload Meeting</span>
          </Link>
        </div>
      </div>

      {/* Mobile Sub-Navigation Bar */}
      <div className="md:hidden flex overflow-x-auto gap-2 px-4 py-2 border-t border-[#681F32] bg-[#3D131D] no-scrollbar">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.path;
          return (
            <Link
              key={item.path}
              href={item.path}
              className={`shrink-0 px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 ${
                isActive 
                  ? "bg-[#FBF8F1] text-[#4A1724]" 
                  : "text-[#E9DFCE] bg-[#681F32]/50"
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
