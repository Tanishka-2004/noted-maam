"use client";

import React, { useState } from "react";
import Link from "next/link";
import { Navigation } from "../../../components/Navigation";
import { DemoModeBanner } from "../../../components/DemoModeBanner";
import { 
  Settings, 
  Users, 
  ShieldCheck, 
  RefreshCw, 
  FileText, 
  Lock, 
  Check, 
  Sparkles,
  Building2
} from "lucide-react";

export default function AppSettingsPage() {
  const [activeTab, setActiveTab] = useState<"members" | "recording" | "integrations" | "audit">("audit");

  const auditEvents = [
    { id: "evt_101", event: "DECISION_SUPERSEDED", entity: "Decision #dec_launch", actor: "Rahul Sharma", timestamp: "2026-07-10 14:35:12 UTC", details: "Target launch date superseded from Oct 12 to Oct 19." },
    { id: "evt_102", event: "TASK_CONFIRMED", entity: "Task #tsk_301", actor: "Rohan Varma", timestamp: "2026-07-10 11:20:04 UTC", details: "Status transitioned from SUGGESTED proposal to HUMAN_CONFIRMED." },
    { id: "evt_103", event: "RISK_OVERRIDE", entity: "Workspace Policy", actor: "Sarah Jenkins", timestamp: "2026-07-09 09:15:22 UTC", details: "Manual host override triggered for audio recording." },
    { id: "evt_104", event: "EXTERNAL_SYNC_SUCCEEDED", entity: "Jira Integration", actor: "System Worker", timestamp: "2026-07-09 09:16:00 UTC", details: "Idempotent sync version 1 dispatched to Jira issue NOTED-42." },
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
              <Settings className="w-4 h-4 text-[#681F32]" />
              <span>Workspace Administration & Compliance</span>
            </div>
            <h1 className="text-3xl font-extrabold text-[#4A1724] tracking-tight">Workspace Settings</h1>
            <p className="text-xs text-[#96546A] font-medium mt-1">Configure members, consent policy, external sync, and audit trails.</p>
          </div>

          <div className="flex items-center gap-1.5 bg-[#E9DFCE] p-1 rounded-xl border border-[#CDBEA9]">
            <button
              onClick={() => setActiveTab("audit")}
              className={`px-4 py-2 rounded-lg text-xs font-semibold transition-all flex items-center gap-1.5 ${
                activeTab === "audit" ? "bg-[#681F32] text-[#FBF8F1]" : "text-[#4A1724] hover:bg-[#F7F1E5]"
              }`}
            >
              <FileText className="w-3.5 h-3.5 text-[#FBF8F1]" />
              <span>Audit Log</span>
            </button>
            <button
              onClick={() => setActiveTab("recording")}
              className={`px-4 py-2 rounded-lg text-xs font-semibold transition-all ${
                activeTab === "recording" ? "bg-[#681F32] text-[#FBF8F1]" : "text-[#4A1724] hover:bg-[#F7F1E5]"
              }`}
            >
              Recording & Consent
            </button>
            <button
              onClick={() => setActiveTab("integrations")}
              className={`px-4 py-2 rounded-lg text-xs font-semibold transition-all ${
                activeTab === "integrations" ? "bg-[#681F32] text-[#FBF8F1]" : "text-[#4A1724] hover:bg-[#F7F1E5]"
              }`}
            >
              Integrations
            </button>
            <button
              onClick={() => setActiveTab("members")}
              className={`px-4 py-2 rounded-lg text-xs font-semibold transition-all ${
                activeTab === "members" ? "bg-[#681F32] text-[#FBF8F1]" : "text-[#4A1724] hover:bg-[#F7F1E5]"
              }`}
            >
              Members
            </button>
          </div>
        </div>

        {/* Audit Log View */}
        {activeTab === "audit" && (
          <div className="p-6 rounded-2xl bg-[#F7F1E5] border border-[#CDBEA9] space-y-4">
            <div className="flex items-center justify-between border-b border-[#CDBEA9] pb-4">
              <h2 className="text-sm font-bold text-[#4A1724] uppercase tracking-wider">Enterprise Audit Event Stream (AUDIT_EVENT)</h2>
              <span className="text-xs font-mono text-[#96546A]">Total Recorded: {auditEvents.length}</span>
            </div>

            <div className="space-y-3">
              {auditEvents.map((evt) => (
                <div key={evt.id} className="p-4 rounded-xl bg-[#FBF8F1] border border-[#CDBEA9] space-y-1.5 hover:border-[#7A2940] transition-all">
                  <div className="flex items-center justify-between text-xs font-mono">
                    <span className="font-bold text-[#681F32]">{evt.event}</span>
                    <span className="text-[#96546A]">{evt.timestamp}</span>
                  </div>
                  <div className="text-xs font-bold text-[#4A1724]">{evt.entity}</div>
                  <p className="text-xs text-[#4A1724]">{evt.details}</p>
                  <div className="text-[10px] text-[#96546A] font-mono">Actor: {evt.actor}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Recording Policy */}
        {activeTab === "recording" && (
          <div className="p-6 rounded-2xl bg-[#F7F1E5] border border-[#CDBEA9] space-y-4">
            <h2 className="text-sm font-bold text-[#4A1724] uppercase tracking-wider">Workspace Recording & Consent Policy</h2>
            <div className="p-4 rounded-xl bg-[#FBF8F1] border border-[#CDBEA9] space-y-2 text-xs text-[#4A1724]">
              <div>Workspace Policy: <strong className="text-[#681F32]">COMPLIANCE_RULE</strong></div>
              <div>Default Participant Consent: <strong className="text-[#681F32] font-mono">GRANTED</strong></div>
              <p className="text-[#96546A] pt-1">Recording halts automatically if an external participant declines consent during ingestion.</p>
            </div>
          </div>
        )}

      </main>
    </div>
  );
}
