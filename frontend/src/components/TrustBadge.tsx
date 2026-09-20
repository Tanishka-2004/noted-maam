"use client";

import React from "react";
import { Check, AlertCircle, HelpCircle, AlertTriangle } from "lucide-react";

export type TrustState = "CONFIRMED" | "CONFLICTING" | "UNKNOWN" | "PARTIAL";

interface TrustBadgeProps {
  state: TrustState;
  customLabel?: string;
  size?: "sm" | "md";
}

export function TrustBadge({ state, customLabel, size = "sm" }: TrustBadgeProps) {
  const sizeClasses = size === "sm" ? "px-2.5 py-0.5 text-[11px]" : "px-3 py-1 text-xs";

  if (state === "CONFIRMED") {
    return (
      <span className={`font-mono font-bold rounded-md bg-emerald-100 border border-emerald-400 text-emerald-950 flex items-center gap-1.5 inline-flex shadow-sm ${sizeClasses}`}>
        <span className="w-2 h-2 rounded-full bg-emerald-600 animate-pulse shrink-0" />
        <Check className="w-3.5 h-3.5 text-emerald-700 shrink-0" />
        <span>{customLabel || "CONFIRMED · Human verified"}</span>
      </span>
    );
  }

  if (state === "CONFLICTING") {
    return (
      <span className={`font-mono font-bold rounded-md bg-amber-100 border border-amber-400 text-amber-950 flex items-center gap-1.5 inline-flex shadow-sm ${sizeClasses}`}>
        <span className="w-2 h-2 rounded-full bg-amber-500 shrink-0" />
        <AlertTriangle className="w-3.5 h-3.5 text-amber-700 shrink-0" />
        <span>{customLabel || "CONFLICTING · Sources disagree"}</span>
      </span>
    );
  }

  if (state === "PARTIAL") {
    return (
      <span className={`font-mono font-bold rounded-md bg-rose-100 border border-rose-400 text-rose-950 flex items-center gap-1.5 inline-flex shadow-sm ${sizeClasses}`}>
        <span className="w-2 h-2 rounded-full bg-rose-600 shrink-0" />
        <AlertCircle className="w-3.5 h-3.5 text-rose-700 shrink-0" />
        <span>{customLabel || "PARTIAL · Extraction Incomplete"}</span>
      </span>
    );
  }

  return (
    <span className={`font-mono font-bold rounded-md bg-[#E9DFCE] text-[#4A1724] border border-[#CDBEA9] flex items-center gap-1.5 inline-flex shadow-sm ${sizeClasses}`}>
      <HelpCircle className="w-3.5 h-3.5 text-[#96546A] shrink-0" />
      <span>{customLabel || "UNKNOWN · Insufficient evidence"}</span>
    </span>
  );
}
