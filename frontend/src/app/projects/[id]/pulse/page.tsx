"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { Navigation } from "../../../../components/Navigation";
import { TrustBadge } from "../../../../components/TrustBadge";
import { DemoModeBanner } from "../../../../components/DemoModeBanner";
import { 
  Activity, 
  AlertOctagon, 
  Clock, 
  AlertTriangle, 
  GitCommit, 
  CheckSquare, 
  ArrowLeft, 
  ChevronRight, 
  Sparkles,
  ShieldCheck
} from "lucide-react";

export default function ProjectPulsePage() {
  const params = useParams();

  const pulseCounters = [
    { label: "Open Blockers", value: 3, unit: "blockers", badge: "PARTIAL" as const },
    { label: "Overdue Commitments", value: 2, unit: "commitments", badge: "PARTIAL" as const },
    { label: "Unresolved Conflicts", value: 1, unit: "disagreements", badge: "CONFLICTING" as const },
    { label: "Decision Changes", value: 4, unit: "supersessions", badge: "CONFIRMED" as const },
  ];

  const recentChanges = [
    {
      id: "chg_1",
      date: "Today at 14:32 UTC",
      type: "DECISION_SUPERSEDED",
      title: "Launch Target Date Moved to October 19th",
      previous: "October 12th",
      new: "October 19th",
      actor: "Rahul Sharma",
      evidence: "Meeting 'Q3 Product Architecture Alignment' (32:35)",
    },
    {
      id: "chg_2",
      date: "Yesterday at 11:15 UTC",
      type: "TASK_CONFIRMED",
      title: "Finalize OpenAPI contract endpoints by Friday afternoon",
      previous: "SUGGESTED",
      new: "HUMAN_CONFIRMED",
      actor: "Rohan Varma",
      evidence: "Meeting 'Auth Gateway Deep Dive' (18:22)",
    },
    {
      id: "chg_3",
      date: "Jul 08 at 09:40 UTC",
      type: "CONFLICT_DETECTED",
      title: "Position Disagreement: Telemetry Compliance vs Launch Window",
      previous: "UNRESOLVED",
      new: "DEFERRED",
      actor: "Sarah Jenkins",
      evidence: "Meeting 'Security Compliance Audit'",
    }
  ];

  return (
    <div className="min-h-screen bg-[#FBF8F1] text-[#4A1724] pb-16">
      <DemoModeBanner />
      <Navigation />

      <main className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 pt-8 space-y-8">
        
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[#CDBEA9] pb-6">
          <div>
            <div className="flex items-center gap-2 text-xs font-mono text-[#681F32] font-bold mb-1">
              <Activity className="w-4 h-4 text-[#681F32]" />
              <span>Project Pulse — Change Detection Engine</span>
            </div>
            <h1 className="text-3xl font-extrabold text-[#4A1724] tracking-tight">Project Alpha Pulse</h1>
            <p className="text-xs text-[#96546A] font-medium mt-1">Answers <strong>"What changed since last week?"</strong> using deterministic status counters.</p>
          </div>

          <div className="flex items-center gap-3">
            <Link
              href="/app/knowledge?tab=decisions"
              className="px-4 py-2 rounded-xl bg-[#681F32] text-[#FBF8F1] text-xs font-semibold hover:bg-[#4A1724] transition-all flex items-center gap-2 shadow-md"
            >
              <GitCommit className="w-3.5 h-3.5 text-[#FBF8F1]" />
              <span>View Decision Timeline</span>
            </Link>
          </div>
        </div>

        {/* Deterministic Health Counters Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {pulseCounters.map((counter, i) => (
            <div key={i} className="p-6 rounded-2xl bg-[#F7F1E5] border border-[#CDBEA9] space-y-3 hover:border-[#7A2940] transition-all">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-[#4A1724] uppercase tracking-wider">{counter.label}</span>
                <TrustBadge state={counter.badge} size="sm" />
              </div>
              <div className="flex items-baseline gap-2">
                <span className="text-4xl font-extrabold text-[#681F32]">{counter.value}</span>
                <span className="text-xs text-[#96546A] font-mono">{counter.unit}</span>
              </div>
              <div className="text-[11px] text-[#96546A] border-t border-[#CDBEA9] pt-2 flex items-center justify-between">
                <span>Deterministic Counter</span>
                <span className="text-[#681F32] font-mono font-bold">No black-box AI score</span>
              </div>
            </div>
          ))}
        </div>

        {/* Project Change Feed */}
        <div className="p-6 rounded-2xl bg-[#F7F1E5] border border-[#CDBEA9] space-y-6">
          <div className="flex items-center justify-between border-b border-[#CDBEA9] pb-4">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-[#681F32]" />
              <h2 className="text-base font-bold text-[#4A1724]">Project Change Log</h2>
            </div>
            <span className="text-xs font-mono text-[#96546A]">Audit Stream: Verified events only</span>
          </div>

          <div className="space-y-4">
            {recentChanges.map((change) => (
              <div key={change.id} className="p-4 rounded-xl bg-[#FBF8F1] border border-[#CDBEA9] space-y-2 hover:border-[#7A2940] transition-all">
                <div className="flex items-center justify-between text-xs font-mono">
                  <span className="font-bold text-[#681F32]">{change.type}</span>
                  <span className="text-[#96546A]">{change.date}</span>
                </div>

                <h3 className="font-bold text-sm text-[#4A1724]">{change.title}</h3>

                <div className="flex flex-wrap items-center gap-3 text-xs text-[#4A1724] bg-[#E9DFCE]/60 p-2.5 rounded-lg border border-[#CDBEA9]">
                  <div>Previous: <code className="text-[#681F32] font-bold">{change.previous}</code></div>
                  <span>→</span>
                  <div>New: <code className="text-[#681F32] font-bold">{change.new}</code></div>
                  <span className="text-[#96546A]">•</span>
                  <div>Actor: <span className="text-[#4A1724] font-semibold">{change.actor}</span></div>
                </div>

                <div className="text-[11px] text-[#96546A] font-mono pt-1">
                  Evidence: {change.evidence}
                </div>
              </div>
            ))}
          </div>
        </div>

      </main>
    </div>
  );
}
