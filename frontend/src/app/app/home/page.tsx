"use client";

import React, { useState } from "react";
import Link from "next/link";
import { Navigation } from "../../../components/Navigation";
import { TrustBadge } from "../../../components/TrustBadge";
import { ProvenanceDrawer, ProvenanceData } from "../../../components/ProvenanceDrawer";
import { DemoModeBanner } from "../../../components/DemoModeBanner";
import { useAppMode } from "../../../context/AppModeContext";
import { 
  Activity, 
  Clock, 
  AlertTriangle, 
  GitCommit, 
  CheckCircle2, 
  ArrowRight, 
  Sparkles, 
  Calendar,
  FileText,
  AlertOctagon,
  ChevronRight,
  ShieldCheck,
  Plus
} from "lucide-react";

export default function AppHomePage() {
  const { mode } = useAppMode();
  const [activeProvenance, setActiveProvenance] = useState<ProvenanceData | null>(null);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const needsAttentionSummary = [
    { count: "02", label: "Overdue commitments", project: "Project Nova", href: "/app/work?tab=verification" },
    { count: "01", label: "Decision changed", project: "Pricing Model", href: "/app/knowledge?tab=decisions" },
    { count: "01", label: "Meeting needs verification", project: "Product Review", href: "/app/meetings/demo-meeting-1" },
  ];

  const projectPulseSummary = [
    { project: "Nova", status: "Needs attention", badge: "bg-amber-100 border border-amber-300 text-amber-950" },
    { project: "LaunchPad", status: "Healthy", badge: "bg-emerald-100 border border-emerald-300 text-emerald-950" },
    { project: "Website", status: "Healthy", badge: "bg-emerald-100 border border-emerald-300 text-emerald-950" },
  ];

  const todaysSchedule = [
    { time: "09:30", title: "Product Review & Architecture Sync", status: "Processed" },
    { time: "11:00", title: "Marketing Strategy & Campaign Sync", status: "Upcoming" },
    { time: "14:00", title: "1:1 Sync — Rahul Sharma", status: "Upcoming" },
  ];

  return (
    <div className="min-h-screen bg-[#FBF8F1] text-[#4A1724] pb-16">
      <DemoModeBanner />
      <Navigation />
      <ProvenanceDrawer data={activeProvenance} onClose={() => setActiveProvenance(null)} />

      {toastMessage && (
        <div className="fixed bottom-6 right-6 z-50 bg-[#681F32] text-[#FBF8F1] px-5 py-3 rounded-xl shadow-2xl flex items-center gap-2 text-xs font-semibold animate-bounce">
          <Sparkles className="w-4 h-4 text-[#FBF8F1]" />
          <span>{toastMessage}</span>
        </div>
      )}

      <main className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 pt-8 space-y-8">
        
        {/* Action-Oriented Header Greeting */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[#CDBEA9] pb-6">
          <div>
            <div className="flex items-center gap-2 text-xs font-mono text-[#681F32] font-bold mb-1">
              <Sparkles className="w-4 h-4 text-[#681F32]" />
              <span>{mode === "DEMO" ? "Daily Executive Operational Briefing (Demo Mode)" : "Real-World Production Intelligence Briefing"}</span>
            </div>
            <h1 className="text-3xl font-extrabold text-[#4A1724] tracking-tight">Good morning, Tanishka.</h1>
            <p className="text-xs text-[#96546A] font-medium mt-1">
              {mode === "DEMO" ? "3 things require your operational attention today in sample workspace." : "Connected to live database. Upload recordings to generate verified task commitments."}
            </p>
          </div>

          <div className="flex items-center gap-3">
            <Link
              href="/onboarding"
              className="px-4 py-2.5 rounded-xl bg-[#681F32] hover:bg-[#4A1724] text-[#FBF8F1] font-semibold text-xs flex items-center gap-2 shadow-md transition-all"
            >
              <Plus className="w-4 h-4 text-[#FBF8F1]" />
              <span>Upload New Recording</span>
            </Link>
          </div>
        </div>

        {/* Mode Dependent Operational Content */}
        {mode === "REAL" ? (
          <div className="p-8 rounded-2xl bg-white border-2 border-emerald-500/30 shadow-sm space-y-6">
            <div className="flex items-center justify-between border-b border-[#CDBEA9] pb-4">
              <div className="flex items-center gap-2 text-xs font-mono text-emerald-700 font-bold uppercase">
                <ShieldCheck className="w-4 h-4 text-emerald-600" />
                <span>Real-World Backend Active (FastAPI DB connected)</span>
              </div>
              <span className="text-xs font-mono px-2.5 py-1 rounded bg-emerald-100 text-emerald-950 font-bold">LIVE SYSTEM</span>
            </div>

            <div className="p-6 rounded-xl bg-[#F7F1E5] border border-[#CDBEA9] text-center space-y-4">
              <h3 className="font-extrabold text-lg text-[#4A1724]">Ready to Process Real Conversations</h3>
              <p className="text-xs text-[#96546A] max-w-lg mx-auto leading-relaxed">
                Your live production workspace is active. Upload audio recordings (`.wav`, `.mp3`, `.m4a`) or stream live meeting audio to extract verified action items, decision lineage, and searchable project memory.
              </p>
              <div className="pt-2 flex items-center justify-center gap-4">
                <Link
                  href="/onboarding"
                  className="px-5 py-2.5 rounded-xl bg-[#681F32] hover:bg-[#4A1724] text-[#FBF8F1] text-xs font-bold transition-all shadow-md flex items-center gap-2"
                >
                  <Plus className="w-4 h-4" />
                  <span>Upload Recording to Live Database</span>
                </Link>
              </div>
            </div>
          </div>
        ) : (
          <>
            {/* Primary Needs Attention Container */}
            <div className="p-6 rounded-2xl bg-[#F7F1E5] border border-[#CDBEA9] shadow-sm space-y-6">
              <div className="flex items-center justify-between border-b border-[#CDBEA9] pb-3">
                <span className="text-xs font-bold text-[#681F32] uppercase tracking-wider font-mono">NEEDS ATTENTION TODAY</span>
                <span className="text-[11px] font-mono text-[#96546A]">Action Required</span>
              </div>

              <div className="space-y-3">
                {needsAttentionSummary.map((item, idx) => (
                  <div key={idx} className="p-4 rounded-xl bg-[#FBF8F1] border border-[#CDBEA9] flex items-center justify-between hover:bg-[#E9DFCE] transition-all">
                    <div className="flex items-center gap-4">
                      <span className="text-lg font-mono font-bold text-[#681F32] w-8">{item.count}</span>
                      <div>
                        <h3 className="font-bold text-sm text-[#4A1724]">{item.label}</h3>
                        <span className="text-xs text-[#96546A] font-mono">{item.project}</span>
                      </div>
                    </div>

                    <Link
                      href={item.href}
                      className="px-3.5 py-1.5 rounded-lg bg-[#681F32] text-[#FBF8F1] text-xs font-semibold hover:bg-[#4A1724] transition-all flex items-center gap-1 font-mono"
                    >
                      <span>REVIEW →</span>
                    </Link>
                  </div>
                ))}
              </div>
            </div>

            {/* Project Pulse Section */}
            <div className="p-6 rounded-2xl bg-[#F7F1E5] border border-[#CDBEA9] space-y-4">
              <div className="flex items-center justify-between border-b border-[#CDBEA9] pb-4">
                <div className="flex items-center gap-2">
                  <Activity className="w-4 h-4 text-[#681F32]" />
                  <h2 className="text-base font-bold text-[#4A1724]">PROJECT PULSE</h2>
                </div>
                <Link href="/app/projects" className="text-xs text-[#681F32] hover:underline flex items-center gap-1 font-mono font-bold">
                  <span>View All Projects</span>
                  <ChevronRight className="w-3.5 h-3.5" />
                </Link>
              </div>

              <div className="space-y-3">
                {projectPulseSummary.map((p, i) => (
                  <div key={i} className="p-4 rounded-xl bg-[#FBF8F1] border border-[#CDBEA9] flex items-center justify-between">
                    <span className="font-bold text-sm text-[#4A1724]">{p.project}</span>
                    <span className={`text-[10px] font-mono font-bold px-2.5 py-1 rounded ${p.badge}`}>
                      {p.status}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Today's Schedule */}
            <div className="p-6 rounded-2xl bg-[#F7F1E5] border border-[#CDBEA9] space-y-4">
              <div className="flex items-center gap-2 border-b border-[#CDBEA9] pb-4">
                <Calendar className="w-4 h-4 text-[#681F32]" />
                <h2 className="text-base font-bold text-[#4A1724]">TODAY'S SCHEDULE</h2>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {todaysSchedule.map((s, idx) => (
                  <div key={idx} className="p-4 rounded-xl bg-[#FBF8F1] border border-[#CDBEA9] flex items-center justify-between">
                    <div>
                      <span className="text-xs font-mono font-bold text-[#681F32]">{s.time}</span>
                      <h3 className="font-bold text-xs text-[#4A1724] mt-0.5">{s.title}</h3>
                    </div>
                    <span className={`text-[10px] font-mono px-2 py-0.5 rounded ${
                      s.status === "Processed" ? "bg-[#681F32] text-[#FBF8F1]" : "bg-[#E9DFCE] text-[#4A1724]"
                    }`}>
                      {s.status}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </>
        )}

      </main>
    </div>
  );
}
