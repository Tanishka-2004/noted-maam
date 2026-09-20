"use client";

import React from "react";
import { Sparkles, Database, ArrowRightLeft, ShieldCheck, Zap } from "lucide-react";
import { useAppMode } from "../context/AppModeContext";

export function DemoModeBanner() {
  const { mode, toggleMode } = useAppMode();

  return (
    <div className={`border-b py-2 px-4 text-xs font-mono transition-all duration-300 ${
      mode === "DEMO"
        ? "bg-[#E9DFCE] border-[#CDBEA9] text-[#4A1724]"
        : "bg-emerald-950 border-emerald-800 text-emerald-100"
    }`}>
      <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          {mode === "DEMO" ? (
            <>
              <Sparkles className="w-4 h-4 text-[#681F32] shrink-0" />
              <span>
                <strong className="text-[#681F32] uppercase">DEMO MODE ACTIVE</strong> — Exploring sample portfolio dataset for Project Alpha & Unassigned Ingestion Inbox
              </span>
            </>
          ) : (
            <>
              <Zap className="w-4 h-4 text-emerald-400 shrink-0 animate-pulse" />
              <span>
                <strong className="text-emerald-300 uppercase">REAL-WORLD PRODUCTION MODE ACTIVE</strong> — Connected to Live FastAPI Engine (`localhost:8000`). Upload real audio recordings & query database memory accurately.
              </span>
            </>
          )}
        </div>

        <button
          onClick={toggleMode}
          className={`px-3 py-1 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all shrink-0 shadow-sm ${
            mode === "DEMO"
              ? "bg-[#681F32] text-[#FBF8F1] hover:bg-[#4A1724]"
              : "bg-emerald-400 text-emerald-950 hover:bg-emerald-300"
          }`}
        >
          <ArrowRightLeft className="w-3.5 h-3.5" />
          <span>{mode === "DEMO" ? "Switch to Real-World Mode" : "Switch to Demo Mode"}</span>
        </button>
      </div>
    </div>
  );
}
