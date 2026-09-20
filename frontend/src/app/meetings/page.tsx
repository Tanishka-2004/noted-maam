"use client";

import React, { useState } from "react";
import Link from "next/link";
import { Navigation } from "../../components/Navigation";
import { TrustBadge } from "../../components/TrustBadge";
import { DemoModeBanner } from "../../components/DemoModeBanner";
import { 
  Video, 
  Inbox, 
  CheckCircle2, 
  AlertTriangle, 
  Clock, 
  ArrowRight, 
  Search, 
  Plus
} from "lucide-react";

export default function MeetingsPage() {
  const [activeTab, setActiveTab] = useState<"all" | "unassigned" | "assigned">("all");
  const [searchTerm, setSearchTerm] = useState("");

  const meetings = [
    {
      id: "demo-meeting-1",
      title: "Q3 Engineering Architecture & Auth Gateway Sync",
      project: "Project Alpha",
      projectId: "proj_alpha",
      status: "READY" as const,
      duration: "42 min",
      date: "2026-07-10 14:30 UTC",
      participants: 4,
      actionsCount: 3,
      decisionsCount: 2,
    },
    {
      id: "meeting-unassigned-1",
      title: "Client Requirements Ingestion — Post-Mortem",
      project: "Unassigned Inbox",
      projectId: null,
      status: "READY" as const,
      duration: "28 min",
      date: "2026-07-09 11:00 UTC",
      participants: 3,
      actionsCount: 2,
      decisionsCount: 1,
    },
    {
      id: "meeting-partial-1",
      title: "Security & Telemetry Compliance Review",
      project: "Project Alpha",
      projectId: "proj_alpha",
      status: "PARTIAL" as const,
      duration: "55 min",
      date: "2026-07-08 09:15 UTC",
      participants: 5,
      actionsCount: 0,
      decisionsCount: 1,
      partialNotice: "Transcript available — Action extraction temporarily failed."
    }
  ];

  const filtered = meetings.filter((m) => {
    if (activeTab === "unassigned") return m.projectId === null;
    if (activeTab === "assigned") return m.projectId !== null;
    return true;
  }).filter(m => m.title.toLowerCase().includes(searchTerm.toLowerCase()));

  return (
    <div className="min-h-screen bg-[#FBF8F1] text-[#4A1724] pb-16">
      <DemoModeBanner />
      <Navigation />

      <main className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 pt-8 space-y-8">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[#CDBEA9] pb-6">
          <div>
            <div className="flex items-center gap-2 text-xs font-mono text-[#681F32] font-bold mb-1">
              <Video className="w-4 h-4 text-[#681F32]" />
              <span>Meeting Directory & Ingestion Hub</span>
            </div>
            <h1 className="text-3xl font-extrabold text-[#4A1724] tracking-tight">Meetings & Unassigned Inbox</h1>
            <p className="text-xs text-[#96546A] font-medium mt-1">Upload meeting recordings first; assign to primary projects anytime.</p>
          </div>

          <Link
            href="/onboarding"
            className="px-4 py-2.5 rounded-xl bg-[#681F32] hover:bg-[#4A1724] text-[#FBF8F1] font-semibold text-xs flex items-center gap-2 transition-all shadow-md"
          >
            <Plus className="w-4 h-4 text-[#FBF8F1]" />
            <span>Upload New Recording</span>
          </Link>
        </div>

        {/* Tab Filters & Search Bar */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2 bg-[#E9DFCE] p-1 rounded-xl border border-[#CDBEA9] w-full sm:w-auto">
            <button
              onClick={() => setActiveTab("all")}
              className={`px-4 py-2 rounded-lg text-xs font-semibold transition-all ${
                activeTab === "all" ? "bg-[#681F32] text-[#FBF8F1]" : "text-[#4A1724] hover:bg-[#F7F1E5]"
              }`}
            >
              All Meetings ({meetings.length})
            </button>
            <button
              onClick={() => setActiveTab("unassigned")}
              className={`px-4 py-2 rounded-lg text-xs font-semibold transition-all flex items-center gap-1.5 ${
                activeTab === "unassigned" ? "bg-[#681F32] text-[#FBF8F1]" : "text-[#4A1724] hover:bg-[#F7F1E5]"
              }`}
            >
              <Inbox className="w-3.5 h-3.5" />
              <span>Unassigned Inbox (1)</span>
            </button>
            <button
              onClick={() => setActiveTab("assigned")}
              className={`px-4 py-2 rounded-lg text-xs font-semibold transition-all ${
                activeTab === "assigned" ? "bg-[#681F32] text-[#FBF8F1]" : "text-[#4A1724] hover:bg-[#F7F1E5]"
              }`}
            >
              Assigned Projects (2)
            </button>
          </div>

          <div className="relative w-full sm:w-72">
            <Search className="w-4 h-4 text-[#96546A] absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Search meetings by title..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full bg-[#FBF8F1] border border-[#CDBEA9] rounded-xl pl-9 pr-4 py-2 text-xs text-[#4A1724] outline-none focus:border-[#681F32]"
            />
          </div>
        </div>

        {/* Meeting Cards List */}
        <div className="grid grid-cols-1 gap-4">
          {filtered.map((meeting) => (
            <div key={meeting.id} className="p-6 rounded-2xl bg-[#F7F1E5] border border-[#CDBEA9] space-y-4 hover:border-[#7A2940] transition-all">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2 mb-1.5">
                    {meeting.projectId === null ? (
                      <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-[#E9DFCE] text-[#4A1724] border border-[#CDBEA9]">
                        Unassigned Inbox
                      </span>
                    ) : (
                      <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-[#681F32] text-[#FBF8F1]">
                        {meeting.project}
                      </span>
                    )}

                    <TrustBadge state={meeting.status === "READY" ? "CONFIRMED" : "PARTIAL"} customLabel={meeting.status} />
                  </div>

                  <h3 className="text-base font-bold text-[#4A1724]">{meeting.title}</h3>
                  <div className="flex items-center gap-4 text-xs text-[#96546A] mt-1 font-mono">
                    <span>{meeting.date}</span>
                    <span>•</span>
                    <span>Duration: {meeting.duration}</span>
                    <span>•</span>
                    <span>{meeting.participants} Participants</span>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <Link
                    href={`/meetings/${meeting.id}`}
                    className="px-4 py-2 rounded-xl bg-[#681F32] hover:bg-[#4A1724] text-[#FBF8F1] text-xs font-semibold flex items-center gap-1.5 shadow-md"
                  >
                    <span>Open Outcome Workspace</span>
                    <ArrowRight className="w-3.5 h-3.5 text-[#FBF8F1]" />
                  </Link>
                </div>
              </div>

              {meeting.status === "PARTIAL" && (
                <div className="p-3 rounded-xl bg-[#F4E8EA] border border-[#96546A] text-[#4A1724] text-xs flex items-center justify-between">
                  <span className="flex items-center gap-2 font-mono">
                    <AlertTriangle className="w-4 h-4 text-[#96546A]" />
                    {meeting.partialNotice}
                  </span>
                  <button className="px-3 py-1 rounded bg-[#681F32] text-[#FBF8F1] font-mono text-[10px] font-bold">
                    Retry Extraction
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      </main>
    </div>
  );
}
