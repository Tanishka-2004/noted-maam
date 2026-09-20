"use client";

import React, { useState } from "react";
import Link from "next/link";
import { Navigation } from "../../components/Navigation";
import { 
  AlertOctagon, 
  Users, 
  FileText, 
  CheckCircle2, 
  Clock, 
  AlertTriangle, 
  Sparkles,
  ArrowRight
} from "lucide-react";

export default function ConflictsPage() {
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [conflictStatus, setConflictStatus] = useState("UNRESOLVED");

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3000);
  };

  const handleResolve = (status: string) => {
    setConflictStatus(status);
    showToast(`Conflict marked as ${status}`);
  };

  return (
    <div className="min-h-screen bg-[#0B0F19] text-gray-100 bg-mesh-dark pb-16">
      <Navigation />

      {/* Toast */}
      {toastMessage && (
        <div className="fixed bottom-6 right-6 z-50 bg-emerald-900 border border-emerald-500 text-emerald-100 px-5 py-3 rounded-xl shadow-2xl flex items-center gap-2 animate-bounce text-xs font-semibold">
          <Sparkles className="w-4 h-4 text-emerald-400" />
          <span>{toastMessage}</span>
        </div>
      )}

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-8 space-y-8">
        
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-white/10 pb-6">
          <div>
            <div className="flex items-center gap-2 text-xs font-mono text-indigo-400 font-semibold mb-1">
              <AlertOctagon className="w-4 h-4 text-indigo-400" />
              <span>Conflict Detection & Resolution Engine</span>
            </div>
            <h1 className="text-3xl font-extrabold text-white tracking-tight">Conflicts & Disagreements Matrix</h1>
            <p className="text-xs text-gray-400 mt-1">Identifies position divergence between speakers across meeting records.</p>
          </div>

          <div className="flex items-center gap-2 text-xs font-mono bg-indigo-500/10 text-indigo-300 px-3 py-1.5 rounded-xl border border-indigo-500/20">
            <span>1 Active Divergence Detected</span>
          </div>
        </div>

        {/* Active Conflict Card */}
        <div className="glass-panel p-6 rounded-2xl border border-indigo-500/30 space-y-6">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-white/10 pb-4">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                  Project Alpha
                </span>
                <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border ${
                  conflictStatus === "RESOLVED"
                    ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/30"
                    : "bg-indigo-500/20 text-indigo-300 border-indigo-500/30"
                }`}>
                  Status: {conflictStatus}
                </span>
              </div>
              <h2 className="text-xl font-bold text-white">Target Launch Window vs Security Telemetry Compliance</h2>
            </div>

            {/* Resolution Controls */}
            <div className="flex items-center gap-2">
              <button
                onClick={() => handleResolve("DEFERRED")}
                className="px-3.5 py-2 rounded-xl border border-white/10 bg-white/5 hover:bg-white/10 text-xs font-semibold text-gray-300"
              >
                Defer Conflict
              </button>
              <button
                onClick={() => handleResolve("RESOLVED")}
                className="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold flex items-center gap-1.5 shadow-md shadow-emerald-950/40"
              >
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>Mark as Resolved</span>
              </button>
            </div>
          </div>

          {/* Position Matrix Side-by-Side Comparison */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            
            {/* Position A: Rahul */}
            <div className="p-5 rounded-xl bg-white/5 border border-white/10 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-emerald-400">Position A — Host / Product Lead</span>
                <span className="text-[10px] font-mono text-gray-400">Speaker: Rahul Sharma</span>
              </div>
              <h3 className="font-bold text-sm text-white">Lock October 19th Launch Date</h3>
              <p className="text-xs text-gray-300">
                Primary constraint is meeting client onboarding window; delay beyond October 19th incurs contractual penalties.
              </p>
              <div className="p-3 rounded-lg bg-black/40 border border-white/5 text-xs italic text-gray-200">
                "No, dashboard Friday drop must happen for client onboarding. Schedule represents our primary goal." (00:41)
              </div>
            </div>

            {/* Position B: Sarah */}
            <div className="p-5 rounded-xl bg-white/5 border border-white/10 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-rose-400">Position B — Security & Telemetry</span>
                <span className="text-[10px] font-mono text-gray-400">Speaker: Sarah Jenkins</span>
              </div>
              <h3 className="font-bold text-sm text-white">Postpone Launch Until Compliance Audit Completes</h3>
              <p className="text-xs text-gray-300">
                Deploying without compliance signoff risks telemetry data leakage and security protocol violation.
              </p>
              <div className="p-3 rounded-lg bg-black/40 border border-white/5 text-xs italic text-gray-200">
                "Deploy Wednesday drop karna target timing ke hisab se block ho sakta hai without security compliance signoff." (00:33)
              </div>
            </div>

          </div>

          <div className="p-4 rounded-xl bg-indigo-950/20 border border-indigo-500/20 text-xs text-indigo-200 flex items-center justify-between">
            <div>
              <strong>Resolution Summary:</strong> Supersession decision created on Decision Timeline (Target launch Oct 19th conditionally pending telemetry signoff).
            </div>
            <Link href="/decisions" className="text-indigo-400 font-bold hover:underline flex items-center gap-1">
              <span>View Decision Record</span>
              <ArrowRight className="w-3 h-3" />
            </Link>
          </div>
        </div>

      </main>
    </div>
  );
}
