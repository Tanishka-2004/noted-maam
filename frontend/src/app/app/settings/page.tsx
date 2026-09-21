"use client";

import React, { useState } from "react";
import Link from "next/link";
import { Navigation } from "../../../components/Navigation";
import { DemoModeBanner } from "../../../components/DemoModeBanner";
import { useAppMode } from "../../../context/AppModeContext";
import { 
  Settings, 
  Users, 
  ShieldCheck, 
  RefreshCw, 
  FileText, 
  Lock, 
  Check, 
  Sparkles,
  Building2,
  Sliders
} from "lucide-react";

export default function AppSettingsPage() {
  const { mode } = useAppMode();
  const [activeTab, setActiveTab] = useState<"members" | "recording" | "integrations" | "audit">("audit");

  const demoAuditEvents = [
    { id: "evt_101", event: "DECISION_SUPERSEDED", entity: "Decision #dec_launch", actor: "Rahul Sharma", timestamp: "2026-07-10 14:35:12 UTC", details: "Target launch date superseded from Oct 12 to Oct 19." },
    { id: "evt_102", event: "TASK_CONFIRMED", entity: "Task #tsk_301", actor: "Rohan Varma", timestamp: "2026-07-10 11:20:04 UTC", details: "Status transitioned from SUGGESTED proposal to HUMAN_CONFIRMED." },
    { id: "evt_103", event: "RISK_OVERRIDE", entity: "Workspace Policy", actor: "Sarah Jenkins", timestamp: "2026-07-09 09:15:22 UTC", details: "Manual host override triggered for audio recording." },
    { id: "evt_104", event: "EXTERNAL_SYNC_SUCCEEDED", entity: "Jira Integration", actor: "System Worker", timestamp: "2026-07-09 09:16:00 UTC", details: "Idempotent sync version 1 dispatched to Jira issue NOTED-42." },
  ];

  const auditEvents = mode === "DEMO" ? demoAuditEvents : [];

  return (
    <div className="min-h-screen bg-[#4A1724] text-[#FBF8F1] pb-16 font-sans">
      <DemoModeBanner />
      <Navigation />

      <main className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 pt-8 space-y-8">
        
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[#681F32] pb-6">
          <div>
            <div className="flex items-center gap-2 text-xs font-semibold text-[#E9DFCE] mb-1">
              <Settings className="w-4 h-4 text-[#FBF8F1]" />
              <span>Workspace Administration & Compliance</span>
            </div>
            <h1 className="text-3xl font-extrabold text-[#FBF8F1] tracking-tight font-display">Workspace Settings</h1>
            <p className="text-xs text-[#E9DFCE] font-medium mt-1">Configure members, consent policy, external sync, and audit trails.</p>
          </div>

          <div className="flex items-center gap-1.5 bg-[#5C1D2D] p-1 rounded-xl border border-[#7A2940]">
            <button
              onClick={() => setActiveTab("audit")}
              className={`px-4 py-2 rounded-lg text-xs font-semibold transition-all flex items-center gap-1.5 ${
                activeTab === "audit" ? "bg-[#FBF8F1] text-[#4A1724] font-bold" : "text-[#E9DFCE] hover:text-[#FBF8F1]"
              }`}
            >
              <FileText className="w-3.5 h-3.5" />
              <span>Audit Log</span>
            </button>
            <button
              onClick={() => setActiveTab("recording")}
              className={`px-4 py-2 rounded-lg text-xs font-semibold transition-all ${
                activeTab === "recording" ? "bg-[#FBF8F1] text-[#4A1724] font-bold" : "text-[#E9DFCE] hover:text-[#FBF8F1]"
              }`}
            >
              Recording & Consent
            </button>
            <button
              onClick={() => setActiveTab("integrations")}
              className={`px-4 py-2 rounded-lg text-xs font-semibold transition-all ${
                activeTab === "integrations" ? "bg-[#FBF8F1] text-[#4A1724] font-bold" : "text-[#E9DFCE] hover:text-[#FBF8F1]"
              }`}
            >
              Integrations
            </button>
            <button
              onClick={() => setActiveTab("members")}
              className={`px-4 py-2 rounded-lg text-xs font-semibold transition-all ${
                activeTab === "members" ? "bg-[#FBF8F1] text-[#4A1724] font-bold" : "text-[#E9DFCE] hover:text-[#FBF8F1]"
              }`}
            >
              Members
            </button>
          </div>
        </div>

        {/* Audit Log View */}
        {activeTab === "audit" && (
          <div className="p-6 rounded-2xl bg-[#5C1D2D] border border-[#7A2940] space-y-4 shadow-md">
            <div className="flex items-center justify-between border-b border-[#7A2940] pb-4">
              <h2 className="text-xs font-bold text-[#FBF8F1] uppercase tracking-wider">Enterprise Audit Event Stream (AUDIT_EVENT)</h2>
              <span className="text-xs font-mono text-[#E9DFCE]">Total Recorded: {auditEvents.length}</span>
            </div>

            {mode === "REAL" && auditEvents.length === 0 ? (
              <div className="p-8 text-center space-y-2">
                <ShieldCheck className="w-8 h-8 text-emerald-400 mx-auto" />
                <h3 className="font-bold text-sm text-[#FBF8F1]">No Production Audit Events Logged Yet</h3>
                <p className="text-xs text-[#E9DFCE] max-w-md mx-auto">
                  Audit logs record live security compliance overrides, decision changes, and human verification actions in real-time.
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {auditEvents.map((evt) => (
                  <div key={evt.id} className="p-4 rounded-xl bg-[#4A1724] border border-[#681F32] space-y-1.5 hover:border-[#7A2940] transition-all">
                    <div className="flex items-center justify-between text-xs font-mono">
                      <span className="font-bold text-[#FBF8F1]">{evt.event}</span>
                      <span className="text-[#E9DFCE]">{evt.timestamp}</span>
                    </div>
                    <div className="text-xs font-bold text-[#FBF8F1]">{evt.entity}</div>
                    <p className="text-xs text-[#E9DFCE]">{evt.details}</p>
                    <div className="text-[10px] text-[#E9DFCE] font-mono">Actor: {evt.actor}</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Recording Policy */}
        {activeTab === "recording" && (
          <div className="p-6 rounded-2xl bg-[#5C1D2D] border border-[#7A2940] space-y-4 shadow-md">
            <h2 className="text-xs font-bold text-[#FBF8F1] uppercase tracking-wider">Workspace Recording & Consent Policy</h2>
            <div className="p-4 rounded-xl bg-[#4A1724] border border-[#681F32] space-y-2 text-xs text-[#FBF8F1]">
              <div>Workspace Policy: <strong className="text-[#FBF8F1]">COMPLIANCE_RULE</strong></div>
              <div>Default Participant Consent: <strong className="text-emerald-400 font-mono">GRANTED</strong></div>
              <p className="text-[#E9DFCE] pt-1">Recording halts automatically if an external participant declines consent during ingestion.</p>
            </div>
          </div>
        )}

        {/* Integrations */}
        {activeTab === "integrations" && (
          <div className="p-6 rounded-2xl bg-[#5C1D2D] border border-[#7A2940] space-y-4 shadow-md">
            <h2 className="text-xs font-bold text-[#FBF8F1] uppercase tracking-wider">Connected Systems & Sync Destinations</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="p-4 rounded-xl bg-[#4A1724] border border-[#681F32] space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-xs text-[#FBF8F1]">Jira Cloud</span>
                  <span className="text-[10px] bg-emerald-900/60 text-emerald-200 border border-emerald-500/30 px-2 py-0.5 rounded font-mono">CONNECTED</span>
                </div>
                <p className="text-xs text-[#E9DFCE]">Idempotent sync dispatches confirmed action commitments as Jira issues.</p>
              </div>
              <div className="p-4 rounded-xl bg-[#4A1724] border border-[#681F32] space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-xs text-[#FBF8F1]">Notion Sync</span>
                  <span className="text-[10px] bg-emerald-900/60 text-emerald-200 border border-emerald-500/30 px-2 py-0.5 rounded font-mono">CONNECTED</span>
                </div>
                <p className="text-xs text-[#E9DFCE]">Automatically maps meeting decision trees to Notion databases.</p>
              </div>
            </div>
          </div>
        )}

        {/* Members */}
        {activeTab === "members" && (
          <div className="p-6 rounded-2xl bg-[#5C1D2D] border border-[#7A2940] space-y-4 shadow-md">
            <h2 className="text-xs font-bold text-[#FBF8F1] uppercase tracking-wider">Workspace Members & Access Control</h2>
            <div className="p-4 rounded-xl bg-[#4A1724] border border-[#681F32] flex items-center justify-between text-xs text-[#FBF8F1]">
              <div>
                <div className="font-bold">Tanishka (You)</div>
                <div className="text-[#E9DFCE] text-[11px]">Workspace Owner · Full Administrator</div>
              </div>
              <span className="text-[10px] bg-[#5C1D2D] border border-[#7A2940] px-2.5 py-1 rounded font-bold">OWNER</span>
            </div>
          </div>
        )}

      </main>
    </div>
  );
}

