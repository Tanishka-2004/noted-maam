"use client";

import React, { useState } from "react";
import Link from "next/link";
import { Navigation } from "../../components/Navigation";
import { 
  Activity, 
  CheckSquare, 
  GitCommit, 
  AlertTriangle, 
  Search, 
  ArrowRight, 
  CheckCircle2, 
  X, 
  Sparkles, 
  Layers,
  Clock,
  UserCheck,
  ShieldCheck,
  RefreshCw,
  FileText,
  AlertOctagon,
  ChevronRight
} from "lucide-react";

export default function CommandCenterPage() {
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3500);
  };

  const processingPipeline = [
    { stage: "UPLOADED", status: "completed" },
    { stage: "TRANSCRIBING", status: "completed" },
    { stage: "DIARIZING", status: "completed" },
    { stage: "EXTRACTING", status: "completed" },
    { stage: "INDEXING", status: "active" },
    { stage: "READY", status: "pending" },
  ];

  const suggestedTasks = [
    {
      id: "tsk_101",
      title: "Finalize OpenAPI contract endpoints for v2.1 auth gateway",
      owner: "Rohan Varma",
      speaker: "Rohan",
      time: "32:18",
      quote: "I'll get the API contract finalized by Friday afternoon.",
      project: "Project Alpha",
      priority: "High",
      state: "SUGGESTED",
    },
    {
      id: "tsk_102",
      title: "Verify database migration scripts on staging environment",
      owner: "Aarohi Sharma",
      speaker: "Aarohi",
      time: "14:45",
      quote: "Aarohi will test the Alembic migration on test_iam DB.",
      project: "Unassigned Inbox",
      priority: "Medium",
      state: "SUGGESTED",
    }
  ];

  return (
    <div className="min-h-screen bg-[#0B0F19] text-gray-100 bg-mesh-dark pb-16">
      <Navigation />

      {/* Toast Notification */}
      {toastMessage && (
        <div className="fixed bottom-6 right-6 z-50 bg-emerald-900 border border-emerald-500 text-emerald-100 px-5 py-3 rounded-xl shadow-2xl flex items-center gap-2 animate-bounce text-xs font-semibold">
          <Sparkles className="w-4 h-4 text-emerald-400" />
          <span>{toastMessage}</span>
        </div>
      )}

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-8 space-y-8">
        
        {/* Header Briefing */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-white/10 pb-6">
          <div>
            <div className="flex items-center gap-2 text-xs font-mono text-emerald-400 font-semibold mb-1">
              <Activity className="w-4 h-4 text-emerald-400" />
              <span>Workspace Executive Command Center</span>
            </div>
            <h1 className="text-3xl font-extrabold text-white tracking-tight">Daily Operational Memory Briefing</h1>
            <p className="text-xs text-gray-400 mt-1">Real-time status across 3 active meetings, 2 suggested commitments, and 1 unresolved decision conflict.</p>
          </div>

          <div className="flex items-center gap-3">
            <Link
              href="/search"
              className="px-4 py-2 rounded-xl glass-panel text-xs font-semibold text-gray-200 border border-white/10 flex items-center gap-2 hover:bg-white/10 transition-all"
            >
              <Search className="w-3.5 h-3.5 text-emerald-400" />
              <span>Search Memory</span>
            </Link>
            <Link
              href="/meetings"
              className="px-4 py-2 rounded-xl bg-gradient-to-r from-emerald-600 to-olive-600 text-white text-xs font-semibold hover:opacity-90 transition-opacity flex items-center gap-2 shadow-lg shadow-emerald-950/40"
            >
              <span>View All Meetings</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>

        {/* Processing Pipeline Monitor Banner */}
        <div className="glass-panel p-5 rounded-2xl border border-emerald-500/30 bg-emerald-950/10 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <RefreshCw className="w-4 h-4 text-emerald-400 animate-spin" />
              <span className="text-xs font-bold text-white uppercase tracking-wider">Active Pipeline Processing: Meeting "Q3 Product Architecture Alignment"</span>
            </div>
            <span className="text-[10px] font-mono bg-emerald-500/20 text-emerald-300 px-2.5 py-0.5 rounded-full border border-emerald-500/30">
              Stage: INDEXING
            </span>
          </div>

          {/* Step Track */}
          <div className="grid grid-cols-2 sm:grid-cols-6 gap-2 pt-2">
            {processingPipeline.map((p, idx) => (
              <div 
                key={idx}
                className={`p-2.5 rounded-xl text-center border font-mono text-[10px] ${
                  p.status === "completed"
                    ? "bg-emerald-500/15 border-emerald-500/40 text-emerald-300"
                    : p.status === "active"
                    ? "bg-amber-500/20 border-amber-500 text-amber-300 animate-pulse"
                    : "bg-white/5 border-white/5 text-gray-600"
                }`}
              >
                <div className="font-bold">{p.stage}</div>
                <div className="text-[9px] mt-0.5 text-gray-400">{p.status.toUpperCase()}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Deterministic Metrics Grid (No Black-Box Scores) */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          {[
            { label: "Open Blockers", value: "3", color: "text-rose-400", border: "border-rose-500/20", icon: AlertOctagon },
            { label: "Overdue Commitments", value: "2", color: "text-amber-400", border: "border-amber-500/20", icon: Clock },
            { label: "Unresolved Conflicts", value: "1", color: "text-indigo-400", border: "border-indigo-500/20", icon: AlertTriangle },
            { label: "Decision Changes", value: "4", color: "text-emerald-400", border: "border-emerald-500/20", icon: GitCommit },
            { label: "Last Activity", value: "2h ago", color: "text-gray-300", border: "border-white/10", icon: Activity },
          ].map((m, i) => {
            const Icon = m.icon;
            return (
              <div key={i} className={`glass-panel p-4 rounded-xl border ${m.border} flex items-center justify-between`}>
                <div>
                  <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider block">{m.label}</span>
                  <span className={`text-2xl font-extrabold ${m.color} mt-1 block`}>{m.value}</span>
                </div>
                <Icon className={`w-5 h-5 ${m.color} opacity-80`} />
              </div>
            );
          })}
        </div>

        {/* Main Content Split: Suggested Commitment Verification & Decision Supersession Lineage */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          
          {/* Column 1 & 2: Human Verification Queue */}
          <div className="lg:col-span-2 space-y-6">
            <div className="flex items-center justify-between border-b border-white/10 pb-3">
              <div className="flex items-center gap-2">
                <ShieldCheck className="w-5 h-5 text-emerald-400" />
                <h2 className="text-lg font-bold text-white">Commitment Verification Queue</h2>
                <span className="text-xs font-mono bg-emerald-500/10 text-emerald-400 px-2 py-0.5 rounded border border-emerald-500/20">
                  AI Proposes → Humans Decide
                </span>
              </div>
              <Link href="/tasks" className="text-xs text-emerald-400 hover:underline flex items-center gap-1">
                <span>All Commitments</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </Link>
            </div>

            <div className="space-y-4">
              {suggestedTasks.map((task) => (
                <div key={task.id} className="glass-panel glass-panel-hover p-5 rounded-2xl border border-white/10 space-y-3">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30">
                          {task.state}
                        </span>
                        <span className="text-xs text-gray-400 font-medium">{task.project}</span>
                      </div>
                      <h3 className="font-bold text-sm text-white mt-1.5">{task.title}</h3>
                    </div>
                    <span className="text-xs font-bold text-emerald-400 bg-emerald-950/40 px-2.5 py-1 rounded-lg border border-emerald-500/20 shrink-0">
                      Owner: {task.owner}
                    </span>
                  </div>

                  {/* Provenance Box */}
                  <div className="p-3 rounded-xl bg-white/5 border border-white/5 text-xs text-gray-300 space-y-1">
                    <div className="flex items-center justify-between text-[10px] text-gray-400 font-mono">
                      <span>Speaker: {task.speaker} ({task.time})</span>
                      <span className="text-emerald-400">Extractor: whisper-v3 / actions-v3.1</span>
                    </div>
                    <p className="italic text-gray-300">"{task.quote}"</p>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center justify-between pt-1">
                    <span className="text-[11px] text-gray-400">Evidence status: Verified quote timestamp</span>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => showToast(`Task dismissed: "${task.title.slice(0, 30)}..."`)}
                        className="px-3 py-1.5 rounded-lg border border-white/10 text-gray-400 hover:text-white hover:bg-white/5 text-xs font-semibold transition-all"
                      >
                        Dismiss
                      </button>
                      <button
                        onClick={() => showToast(`Confirmed & Assigned: "${task.title.slice(0, 30)}..."`)}
                        className="px-4 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold shadow-md shadow-emerald-950/40 transition-all flex items-center gap-1.5"
                      >
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        <span>Confirm Commitment</span>
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Column 3: Quick Navigation to Hero Experiences */}
          <div className="space-y-6">
            <div className="border-b border-white/10 pb-3">
              <h2 className="text-lg font-bold text-white">Hero Experiences</h2>
            </div>

            <div className="space-y-4">
              <Link href="/projects/alpha/pulse" className="block glass-panel glass-panel-hover p-5 rounded-2xl border border-olive-500/20">
                <div className="flex items-center gap-2 text-olive-400 text-xs font-bold font-mono uppercase">
                  <Activity className="w-4 h-4" />
                  <span>Project Pulse</span>
                </div>
                <h3 className="font-bold text-sm text-white mt-1">What Changed Since Last Week?</h3>
                <p className="text-xs text-gray-400 mt-1">Track 3 open blockers and 2 overdue commitments on Project Alpha.</p>
              </Link>

              <Link href="/decisions" className="block glass-panel glass-panel-hover p-5 rounded-2xl border border-amber-500/20">
                <div className="flex items-center gap-2 text-amber-400 text-xs font-bold font-mono uppercase">
                  <GitCommit className="w-4 h-4" />
                  <span>Decision Timeline</span>
                </div>
                <h3 className="font-bold text-sm text-white mt-1">How Did We Get Here?</h3>
                <p className="text-xs text-gray-400 mt-1">View launch date supersession tree: Oct 12 → Oct 19 with rationale.</p>
              </Link>

              <Link href="/conflicts" className="block glass-panel glass-panel-hover p-5 rounded-2xl border border-indigo-500/20">
                <div className="flex items-center gap-2 text-indigo-400 text-xs font-bold font-mono uppercase">
                  <AlertOctagon className="w-4 h-4" />
                  <span>Conflicts Matrix</span>
                </div>
                <h3 className="font-bold text-sm text-white mt-1">1 Active Position Disagreement</h3>
                <p className="text-xs text-gray-400 mt-1">Rahul (Oct 19 launch) vs Sarah (Telemetry compliance dependency).</p>
              </Link>
            </div>
          </div>

        </div>
      </main>
    </div>
  );
}
