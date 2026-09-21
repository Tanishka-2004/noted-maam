"use client";

import React, { useState } from "react";
import Link from "next/link";
import { Navigation } from "../../../components/Navigation";
import { TrustBadge } from "../../../components/TrustBadge";
import { ProvenanceDrawer, ProvenanceData } from "../../../components/ProvenanceDrawer";
import { useAppMode } from "../../../context/AppModeContext";
import { 
  CheckSquare, 
  ShieldCheck, 
  AlertOctagon, 
  HelpCircle, 
  Check, 
  RotateCcw, 
  Sparkles,
  ArrowRight,
  Plus
} from "lucide-react";

export default function AppWorkPage() {
  const { mode } = useAppMode();
  const [activeTab, setActiveTab] = useState<"verification" | "my-tasks" | "conflicts">("verification");
  const [activeProvenance, setActiveProvenance] = useState<ProvenanceData | null>(null);
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [confirmedTasks, setConfirmedTasks] = useState<Record<string, boolean>>({});

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3000);
  };

  const toggleConfirm = (taskId: string, title: string) => {
    const nextState = !confirmedTasks[taskId];
    setConfirmedTasks(prev => ({ ...prev, [taskId]: nextState }));
    if (nextState) {
      showToast(`Task confirmed & assigned: "${title.slice(0, 30)}..."`);
    } else {
      showToast(`Reverted state to SUGGESTED`);
    }
  };

  const demoVerificationItems = [
    {
      id: "tsk_301",
      title: "Finalize OpenAPI contract endpoints for v2.1 auth gateway",
      project: "Project Alpha",
      owner: "Rohan Varma",
      deadline: "Friday 17:00 UTC",
      priority: "High",
      state: "SUGGESTED",
      provenance: {
        title: "Finalize OpenAPI contract endpoints",
        sourceMeeting: "Q3 Engineering Architecture Sync",
        timestamp: "32:18",
        timeRange: "32:18-32:25",
        speaker: "Rohan Varma",
        speakerTag: "SPEAKER_01",
        quote: "I'll get the API contract finalized by Friday afternoon so Aarohi can start testing.",
        confidence: "99%",
        extractorVersion: "actions-v3.1",
        reason: "Explicit verbal commitment by Rohan Varma during architecture sync.",
        trustState: "CONFIRMED" as const
      }
    },
    {
      id: "tsk_302",
      title: "Verify database migration scripts on test_iam DB",
      project: "Unassigned Inbox",
      owner: "Aarohi Sharma",
      deadline: "Jul 15 12:00 UTC",
      priority: "Medium",
      state: "SUGGESTED",
      provenance: {
        title: "Verify database migration scripts",
        sourceMeeting: "Client Requirements Post-Mortem",
        timestamp: "14:45",
        timeRange: "14:45-14:52",
        speaker: "Aarohi Sharma",
        speakerTag: "SPEAKER_02",
        quote: "Aarohi will test the Alembic migration on test_iam DB.",
        confidence: "96%",
        extractorVersion: "actions-v3.1",
        reason: "Action item proposed for database migration verification.",
        trustState: "CONFIRMED" as const
      }
    }
  ];

  const verificationItems = mode === "DEMO" ? demoVerificationItems : [];

  return (
    <div className="min-h-screen bg-[#4A1724] text-[#FBF8F1] pb-16 font-sans">
      <Navigation />
      <ProvenanceDrawer data={activeProvenance} onClose={() => setActiveProvenance(null)} />

      {toastMessage && (
        <div className="fixed bottom-6 right-6 z-50 bg-[#FBF8F1] text-[#4A1724] px-5 py-3 rounded-xl shadow-2xl flex items-center gap-2 text-xs font-bold animate-bounce">
          <Sparkles className="w-4 h-4 text-[#4A1724]" />
          <span>{toastMessage}</span>
        </div>
      )}

      <main className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 pt-8 space-y-8">
        
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[#681F32] pb-6">
          <div>
            <div className="flex items-center gap-2 text-xs font-semibold text-[#E9DFCE] mb-1">
              <CheckSquare className="w-4 h-4 text-[#FBF8F1]" />
              <span>Work Center — Accountable Action Queue</span>
            </div>
            <h1 className="text-3xl font-extrabold text-[#FBF8F1] tracking-tight font-display">Work</h1>
            <p className="text-xs text-[#E9DFCE] mt-1 font-medium">Answers <strong>"What do I need to do?"</strong> with strict human verification gates.</p>
          </div>

          {/* Sub-View Tabs */}
          <div className="flex items-center gap-1.5 bg-[#5C1D2D] p-1 rounded-xl border border-[#7A2940]">
            <button
              onClick={() => setActiveTab("verification")}
              className={`px-4 py-2 rounded-lg text-xs font-semibold transition-all flex items-center gap-1.5 ${
                activeTab === "verification" ? "bg-[#FBF8F1] text-[#4A1724] font-bold" : "text-[#E9DFCE] hover:text-[#FBF8F1]"
              }`}
            >
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>Verification Queue ({verificationItems.length})</span>
            </button>
            <button
              onClick={() => setActiveTab("my-tasks")}
              className={`px-4 py-2 rounded-lg text-xs font-semibold transition-all ${
                activeTab === "my-tasks" ? "bg-[#FBF8F1] text-[#4A1724] font-bold" : "text-[#E9DFCE] hover:text-[#FBF8F1]"
              }`}
            >
              My Tasks
            </button>
            <button
              onClick={() => setActiveTab("conflicts")}
              className={`px-4 py-2 rounded-lg text-xs font-semibold transition-all flex items-center gap-1.5 ${
                activeTab === "conflicts" ? "bg-[#FBF8F1] text-[#4A1724] font-bold" : "text-[#E9DFCE] hover:text-[#FBF8F1]"
              }`}
            >
              <AlertOctagon className="w-3.5 h-3.5" />
              <span>Conflicts ({mode === "DEMO" ? 1 : 0})</span>
            </button>
          </div>
        </div>

        {/* Content Render Based on Tab */}
        {activeTab === "verification" && (
          <div className="space-y-4">
            <div className="p-4 rounded-xl bg-[#5C1D2D] border border-[#7A2940] flex items-center justify-between text-xs text-[#FBF8F1] font-medium shadow-md">
              <div className="flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0" />
                <span><strong>AI Proposes, Humans Decide:</strong> Review extracted commitments before assigning to project execution.</span>
              </div>
            </div>

            {mode === "REAL" && verificationItems.length === 0 ? (
              <div className="p-12 rounded-2xl bg-[#5C1D2D] border border-[#7A2940] text-center space-y-4 shadow-md">
                <CheckSquare className="w-12 h-12 text-[#FBF8F1] mx-auto opacity-80" />
                <h3 className="text-lg font-bold text-[#FBF8F1]">No Unverified Commitments in Workspace</h3>
                <p className="text-xs text-[#E9DFCE] max-w-md mx-auto">
                  Your live workspace has no pending action items for human verification. Upload a meeting recording to extract commitments.
                </p>
                <div className="pt-2">
                  <Link
                    href="/onboarding"
                    className="px-5 py-2.5 rounded-xl bg-[#FBF8F1] hover:bg-[#F7F1E5] text-[#4A1724] font-bold text-xs inline-flex items-center gap-2 shadow-md"
                  >
                    <Plus className="w-4 h-4 text-[#4A1724]" />
                    <span>Upload Recording</span>
                  </Link>
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                {verificationItems.map((item) => {
                  const isConfirmed = confirmedTasks[item.id];
                  return (
                    <div key={item.id} className="p-6 rounded-2xl bg-[#5C1D2D] border border-[#7A2940] space-y-4 hover:border-[#96546A] transition-all shadow-md">
                      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                        <div className="space-y-1.5">
                          <div className="flex items-center gap-2">
                            <TrustBadge state={isConfirmed ? "CONFIRMED" : "CONFIRMED"} customLabel={isConfirmed ? "CONFIRMED · Human verified" : "PROPOSED · Needs review"} />
                            <span className="text-[10px] font-semibold text-[#FBF8F1] border border-[#7A2940] px-2 py-0.5 rounded bg-[#4A1724]">{item.project}</span>
                          </div>
                          <h3 className="text-base font-bold text-[#FBF8F1]">{item.title}</h3>
                          <div className="text-xs text-[#E9DFCE] font-medium">
                            Assignee: <strong className="text-[#FBF8F1]">{item.owner}</strong> • Deadline: {item.deadline}
                          </div>
                        </div>

                        {/* Actions */}
                        <div className="flex items-center gap-3">
                          <button
                            onClick={() => setActiveProvenance(item.provenance)}
                            className="px-3.5 py-2 rounded-xl border border-[#7A2940] bg-[#681F32] hover:bg-[#7A2940] text-xs font-semibold text-[#FBF8F1] flex items-center gap-1.5"
                          >
                            <HelpCircle className="w-3.5 h-3.5 text-[#FBF8F1]" />
                            <span>Why am I seeing this?</span>
                          </button>

                          {isConfirmed ? (
                            <button
                              onClick={() => toggleConfirm(item.id, item.title)}
                              className="px-4 py-2 rounded-xl border border-[#7A2940] bg-[#681F32] text-[#FBF8F1] text-xs font-semibold flex items-center gap-1.5"
                            >
                              <RotateCcw className="w-3.5 h-3.5" />
                              <span>Undo Confirmation</span>
                            </button>
                          ) : (
                            <button
                              onClick={() => toggleConfirm(item.id, item.title)}
                              className="px-4 py-2 rounded-xl bg-[#FBF8F1] hover:bg-[#F7F1E5] text-[#4A1724] text-xs font-bold shadow-md flex items-center gap-1.5"
                            >
                              <Check className="w-3.5 h-3.5 text-[#4A1724]" />
                              <span>Confirm & Assign</span>
                            </button>
                          )}
                        </div>
                      </div>

                      <div className="p-3 rounded-xl bg-[#4A1724] border border-[#681F32] text-xs text-[#FBF8F1] flex items-center justify-between font-medium">
                        <div className="italic truncate max-w-2xl">"{item.provenance.quote}"</div>
                        <span className="text-[10px] text-[#E9DFCE] font-bold shrink-0">{item.provenance.timeRange}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {activeTab === "my-tasks" && (
          <div className="p-8 rounded-2xl bg-[#5C1D2D] border border-[#7A2940] text-center space-y-3 shadow-md">
            <CheckSquare className="w-8 h-8 text-[#FBF8F1] mx-auto" />
            <h3 className="font-bold text-[#FBF8F1] text-sm font-display">
              {mode === "DEMO" ? "Your Personal Confirmed Commitments" : "Real Workspace Tasks"}
            </h3>
            <p className="text-xs text-[#E9DFCE] max-w-md mx-auto font-medium">
              {mode === "DEMO" 
                ? '1 active confirmed task assigned to Rohan Varma: "Finalize OpenAPI contract endpoints for v2.1 auth gateway".'
                : 'No tasks currently assigned in live mode. Confirm action items from the verification queue.'}
            </p>
          </div>
        )}

        {activeTab === "conflicts" && (
          <div className="p-6 rounded-2xl bg-[#5C1D2D] border border-[#7A2940] space-y-4 shadow-md">
            {mode === "DEMO" ? (
              <>
                <div className="flex items-center justify-between border-b border-[#7A2940] pb-4">
                  <div className="flex items-center gap-2">
                    <TrustBadge state="CONFLICTING" />
                    <h2 className="text-base font-bold text-[#FBF8F1]">Target Launch Window vs Security Compliance</h2>
                  </div>
                  <Link href="/app/knowledge" className="text-xs text-[#FBF8F1] font-bold hover:underline">
                    Resolve via Decision Timeline →
                  </Link>
                </div>
                <p className="text-xs text-[#E9DFCE] font-medium">Rahul Sharma (Oct 19 launch target) vs Sarah Jenkins (Security compliance audit dependency).</p>
              </>
            ) : (
              <div className="text-center py-6">
                <AlertOctagon className="w-8 h-8 text-emerald-400 mx-auto mb-2" />
                <h3 className="font-bold text-sm text-[#FBF8F1]">Zero Active Speaker Conflicts Detected</h3>
                <p className="text-xs text-[#E9DFCE] mt-1 font-medium">Real-time divergence analysis engine is monitoring incoming audio streams.</p>
              </div>
            )}
          </div>
        )}

      </main>
    </div>
  );
}
