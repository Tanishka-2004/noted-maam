"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { Navigation } from "../../../../../components/Navigation";
import { TrustBadge } from "../../../../../components/TrustBadge";
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
  ShieldCheck,
  Filter,
  X
} from "lucide-react";

export default function AppProjectPulsePage() {
  const params = useParams();
  const [selectedFilter, setSelectedFilter] = useState<string | null>(null);

  const pulseCounters = [
    { id: "BLOCKERS", label: "Open Blockers", value: 3, unit: "blockers", badge: "PARTIAL" as const, matchType: "CONFLICT_DETECTED" },
    { id: "COMMITMENTS", label: "Overdue Commitments", value: 2, unit: "commitments", badge: "PARTIAL" as const, matchType: "TASK_CONFIRMED" },
    { id: "CONFLICTS", label: "Unresolved Conflicts", value: 1, unit: "disagreements", badge: "CONFLICTING" as const, matchType: "CONFLICT_DETECTED" },
    { id: "DECISIONS", label: "Decision Changes", value: 4, unit: "supersessions", badge: "CONFIRMED" as const, matchType: "DECISION_SUPERSEDED" },
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

  const handleCardClick = (id: string) => {
    if (selectedFilter === id) {
      setSelectedFilter(null);
    } else {
      setSelectedFilter(id);
      const el = document.getElementById("change-log-section");
      if (el) el.scrollIntoView({ behavior: "smooth" });
    }
  };

  const activeCounterObj = pulseCounters.find(c => c.id === selectedFilter);
  const filteredChanges = selectedFilter
    ? recentChanges.filter(ch => ch.type === activeCounterObj?.matchType)
    : recentChanges;

  return (
    <div className="min-h-screen bg-[#4A1724] text-[#FBF8F1] pb-16 font-sans">
      <Navigation />

      <main className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 pt-8 space-y-8">
        
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[#681F32] pb-6">
          <div>
            <div className="flex items-center gap-2 text-xs font-semibold text-[#E9DFCE] mb-1">
              <Activity className="w-4 h-4 text-[#FBF8F1]" />
              <span>Project Pulse — Change Detection Engine</span>
            </div>
            <h1 className="text-3xl font-extrabold text-[#FBF8F1] tracking-tight font-display">Project Alpha Pulse</h1>
            <p className="text-xs text-[#E9DFCE] font-medium mt-1">Answers <strong>"What changed since last week?"</strong> using deterministic status counters.</p>
          </div>

          <div className="flex items-center gap-3">
            <Link
              href="/app/knowledge"
              className="px-4 py-2 rounded-xl bg-[#FBF8F1] text-[#4A1724] text-xs font-bold hover:bg-[#F7F1E5] transition-all flex items-center gap-2 shadow-md"
            >
              <GitCommit className="w-3.5 h-3.5 text-[#4A1724]" />
              <span>View Decision Timeline</span>
            </Link>
          </div>
        </div>

        {/* Deterministic Health Counters Grid (Clickable Interactive Cards) */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {pulseCounters.map((counter) => {
            const isSelected = selectedFilter === counter.id;
            return (
              <button
                key={counter.id}
                onClick={() => handleCardClick(counter.id)}
                className={`p-6 rounded-2xl text-left space-y-3 transition-all shadow-md cursor-pointer ${
                  isSelected 
                    ? "bg-[#681F32] border-2 border-[#FBF8F1] shadow-xl scale-[1.02]" 
                    : "bg-[#5C1D2D] border border-[#7A2940] hover:border-[#FBF8F1]/60 hover:bg-[#681F32]/80 hover:scale-[1.01]"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-[#FBF8F1] uppercase tracking-wider">{counter.label}</span>
                  <TrustBadge state={counter.badge} size="sm" />
                </div>
                <div className="flex items-baseline gap-2">
                  <span className="text-4xl font-extrabold text-[#FBF8F1]">{counter.value}</span>
                  <span className="text-xs text-[#E9DFCE] font-medium">{counter.unit}</span>
                </div>
                <div className="text-[11px] text-[#E9DFCE] border-t border-[#7A2940] pt-2 flex items-center justify-between font-medium">
                  <span>{isSelected ? "Active Filter" : "Click to view events"}</span>
                  <span className="text-[#FBF8F1] font-bold">→</span>
                </div>
              </button>
            );
          })}
        </div>

        {/* Project Change Feed */}
        <div id="change-log-section" className="p-6 rounded-2xl bg-[#5C1D2D] border border-[#7A2940] space-y-6 shadow-md scroll-mt-24">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between border-b border-[#7A2940] pb-4 gap-3">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-[#FBF8F1]" />
              <h2 className="text-base font-bold text-[#FBF8F1]">Project Change Log</h2>
            </div>
            
            {selectedFilter ? (
              <div className="flex items-center gap-2">
                <span className="text-xs text-[#FBF8F1] bg-[#681F32] px-3 py-1 rounded-full border border-[#7A2940] font-semibold flex items-center gap-1.5">
                  <Filter className="w-3 h-3 text-[#FBF8F1]" />
                  <span>Filtered: {activeCounterObj?.label}</span>
                </span>
                <button
                  onClick={() => setSelectedFilter(null)}
                  className="text-xs text-[#E9DFCE] hover:text-[#FBF8F1] p-1 rounded-lg hover:bg-[#681F32] transition-colors"
                  title="Clear filter"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            ) : (
              <span className="text-xs text-[#E9DFCE] font-medium">Audit Stream: Verified events only</span>
            )}
          </div>

          <div className="space-y-4">
            {filteredChanges.length === 0 ? (
              <div className="p-8 text-center text-xs text-[#E9DFCE] font-medium">
                No change log events match the selected category.
              </div>
            ) : (
              filteredChanges.map((change) => (
                <div key={change.id} className="p-4 rounded-xl bg-[#4A1724] border border-[#681F32] space-y-2 hover:border-[#7A2940] transition-all">
                  <div className="flex items-center justify-between text-xs font-semibold">
                    <span className="font-bold text-[#FBF8F1]">{change.type}</span>
                    <span className="text-[#E9DFCE]">{change.date}</span>
                  </div>

                  <h3 className="font-bold text-sm text-[#FBF8F1]">{change.title}</h3>

                  <div className="flex flex-wrap items-center gap-3 text-xs text-[#FBF8F1] bg-[#5C1D2D] p-2.5 rounded-lg border border-[#7A2940] font-medium">
                    <div>Previous: <code className="text-[#E9DFCE] font-bold">{change.previous}</code></div>
                    <span>→</span>
                    <div>New: <code className="text-[#FBF8F1] font-bold">{change.new}</code></div>
                    <span className="text-[#E9DFCE]">•</span>
                    <div>Actor: <span className="text-[#FBF8F1] font-semibold">{change.actor}</span></div>
                  </div>

                  <div className="text-[11px] text-[#E9DFCE] pt-1 font-medium">
                    Evidence: {change.evidence}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

      </main>
    </div>
  );
}

