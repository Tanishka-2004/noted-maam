"use client";

import React, { useState } from "react";
import Link from "next/link";
import { Navigation } from "../../../components/Navigation";
import { TrustBadge } from "../../../components/TrustBadge";
import { ProvenanceDrawer, ProvenanceData } from "../../../components/ProvenanceDrawer";
import { useAppMode } from "../../../context/AppModeContext";
import { 
  BookOpen, 
  GitCommit, 
  Search, 
  Lock, 
  Check, 
  AlertTriangle, 
  HelpCircle, 
  FileText, 
  Sparkles,
  ArrowRight,
  Plus
} from "lucide-react";

export default function AppKnowledgePage() {
  const { mode } = useAppMode();
  const [activeTab, setActiveTab] = useState<"decisions" | "search">("decisions");
  const [query, setQuery] = useState(mode === "DEMO" ? "When is the Nova launch?" : "");
  const [activeSearchMode, setActiveSearchMode] = useState<"ANSWERABLE" | "CONFLICTING" | "UNKNOWN">("ANSWERABLE");
  const [activeProvenance, setActiveProvenance] = useState<ProvenanceData | null>(null);

  const demoDecisionsTree = [
    {
      id: "dec_launch",
      topic: "Target Launch Date & Release Window",
      currentStatus: "CONFIRMED" as const,
      project: "Project Alpha",
      versions: [
        {
          version: 2,
          state: "CONFIRMED" as const,
          date: "Jul 10, 2026 (32:35)",
          summary: "Launch target date set to October 19th",
          rationale: "Accommodates telemetry compliance testing window requested by Sarah.",
          speaker: "Rahul Sharma",
          timeRange: "32:35-32:45",
          quote: "Confirmed. Launch target date is locked for October 19th pending telemetry signoff.",
          actor: "Rahul Sharma (Host)",
          provenance: {
            title: "Launch target date set to October 19th",
            sourceMeeting: "Q3 Engineering Architecture Sync",
            timestamp: "32:35",
            timeRange: "32:35-32:45",
            speaker: "Rahul Sharma",
            speakerTag: "SPEAKER_00",
            quote: "Confirmed. Launch target date is locked for October 19th pending telemetry signoff.",
            confidence: "98%",
            extractorVersion: "decisions-v2.1",
            reason: "Confirmed host decision overriding previous October 12th target.",
            trustState: "CONFIRMED" as const
          }
        },
        {
          version: 1,
          state: "SUPERSEDED" as const,
          date: "Jul 01, 2026 (14:10)",
          summary: "Initial launch target date set to October 12th",
          rationale: "Proposed during Q3 planning meeting.",
          speaker: "Aarohi Sharma",
          timeRange: "14:10-14:20",
          quote: "Let's target October 12th for the initial client release.",
          actor: "Aarohi Sharma"
        }
      ]
    }
  ];

  const decisionsTree = mode === "DEMO" ? demoDecisionsTree : [];

  return (
    <div className="min-h-screen bg-[#4A1724] text-[#FBF8F1] pb-16 font-sans">
      <Navigation />
      <ProvenanceDrawer data={activeProvenance} onClose={() => setActiveProvenance(null)} />

      <main className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 pt-8 space-y-8">
        
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[#681F32] pb-6">
          <div>
            <div className="flex items-center gap-2 text-xs font-semibold text-[#E9DFCE] mb-1">
              <BookOpen className="w-4 h-4 text-[#FBF8F1]" />
              <span>Organizational Memory Engine</span>
            </div>
            <h1 className="text-3xl font-extrabold text-[#FBF8F1] tracking-tight font-display">Knowledge</h1>
            <p className="text-xs text-[#E9DFCE] font-medium mt-1">Answers <strong>"Why do we believe this?"</strong> through decision version trees and evidence RAG.</p>
          </div>

          <div className="flex items-center gap-1.5 bg-[#5C1D2D] p-1 rounded-xl border border-[#7A2940]">
            <button
              onClick={() => setActiveTab("decisions")}
              className={`px-4 py-2 rounded-lg text-xs font-semibold transition-all flex items-center gap-1.5 ${
                activeTab === "decisions" ? "bg-[#FBF8F1] text-[#4A1724] font-bold" : "text-[#E9DFCE] hover:text-[#FBF8F1]"
              }`}
            >
              <GitCommit className="w-3.5 h-3.5" />
              <span>Decision Lineage ({decisionsTree.length})</span>
            </button>
            <button
              onClick={() => setActiveTab("search")}
              className={`px-4 py-2 rounded-lg text-xs font-semibold transition-all flex items-center gap-1.5 ${
                activeTab === "search" ? "bg-[#FBF8F1] text-[#4A1724] font-bold" : "text-[#E9DFCE] hover:text-[#FBF8F1]"
              }`}
            >
              <Search className="w-3.5 h-3.5" />
              <span>Search Memory</span>
            </button>
          </div>
        </div>

        {/* Tab 1: Decision Lineage Tree */}
        {activeTab === "decisions" && (
          mode === "REAL" && decisionsTree.length === 0 ? (
            <div className="p-12 rounded-2xl bg-[#5C1D2D] border border-[#7A2940] text-center space-y-4 shadow-md">
              <GitCommit className="w-12 h-12 text-[#FBF8F1] mx-auto opacity-80" />
              <h3 className="text-lg font-bold text-[#FBF8F1]">No Real Decisions Recorded in Workspace</h3>
              <p className="text-xs text-[#E9DFCE] max-w-md mx-auto font-medium">
                Your live workspace is connected. Process a meeting recording to build decision version lineage with audio evidence quotes.
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
            <div className="p-6 rounded-2xl bg-[#5C1D2D] border border-[#7A2940] space-y-6 shadow-md">
              <div className="flex items-center justify-between border-b border-[#7A2940] pb-4">
                <div>
                  <span className="text-[10px] font-bold text-[#E9DFCE] uppercase tracking-wider">Project Alpha</span>
                  <h2 className="text-lg font-extrabold text-[#FBF8F1] mt-0.5">{decisionsTree[0]?.topic}</h2>
                </div>
                <TrustBadge state="CONFIRMED" customLabel="CONFIRMED · Current Decision" />
              </div>

              <div className="space-y-6 relative before:absolute before:left-4 before:top-2 before:bottom-2 before:w-0.5 before:bg-[#7A2940]">
                {decisionsTree[0]?.versions.map((ver, idx) => (
                  <div key={idx} className="relative pl-10 space-y-3">
                    <div className={`absolute left-2.5 top-1.5 w-3.5 h-3.5 rounded-full border-2 ${
                      ver.state === "CONFIRMED" ? "bg-[#FBF8F1] border-[#FBF8F1]" : "bg-[#96546A] border-[#96546A]"
                    }`} />

                    <div className="p-4 rounded-xl bg-[#4A1724] border border-[#681F32] space-y-2">
                      <div className="flex items-center justify-between text-xs font-medium">
                        <span className={`font-bold px-2 py-0.5 rounded text-[10px] ${
                          ver.state === "SUPERSEDED" 
                            ? "bg-[#681F32] text-[#E9DFCE] border border-[#7A2940]" 
                            : "bg-[#FBF8F1] text-[#4A1724]"
                        }`}>
                          v{ver.version} — {ver.state}
                        </span>
                        <span className="text-[#E9DFCE]">{ver.date}</span>
                      </div>

                      <h4 className="font-bold text-sm text-[#FBF8F1]">{ver.summary}</h4>
                      <p className="text-xs text-[#E9DFCE] font-medium">{ver.rationale}</p>

                      <div className="p-3 rounded-lg bg-[#5C1D2D] border border-[#7A2940] text-xs text-[#FBF8F1] space-y-1 mt-2 font-medium">
                        <div className="flex justify-between text-[10px] text-[#E9DFCE]">
                          <span>Speaker: {ver.speaker} ({ver.timeRange})</span>
                          {ver.provenance && (
                            <button
                              onClick={() => setActiveProvenance(ver.provenance!)}
                              className="text-[#FBF8F1] font-bold hover:underline"
                            >
                              Why am I seeing this?
                            </button>
                          )}
                        </div>
                        <p className="italic text-[#FBF8F1]">"{ver.quote}"</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )
        )}

        {/* Tab 2: Searchable Project Memory */}
        {activeTab === "search" && (
          <div className="space-y-6">
            <div className="p-4 rounded-2xl bg-[#5C1D2D] border border-[#7A2940] space-y-4 shadow-md">
              <div className="flex items-center gap-3 bg-[#4A1724] border border-[#681F32] rounded-xl px-4 py-3 focus-within:border-[#FBF8F1] transition-all">
                <Search className="w-5 h-5 text-[#E9DFCE] shrink-0" />
                <input
                  type="text"
                  placeholder="Ask a question about project memory..."
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  className="w-full bg-transparent border-none outline-none text-[#FBF8F1] text-sm font-medium placeholder:text-[#E9DFCE]/60"
                />
                <button
                  onClick={() => setActiveSearchMode(query.trim() ? "ANSWERABLE" : "UNKNOWN")}
                  className="px-5 py-2 rounded-xl bg-[#FBF8F1] text-[#4A1724] font-bold text-xs shrink-0 hover:bg-[#F7F1E5]"
                >
                  Search Memory
                </button>
              </div>
            </div>

            <div className="p-6 rounded-2xl bg-[#5C1D2D] border border-[#7A2940] space-y-4 shadow-md">
              <div className="flex items-center justify-between border-b border-[#7A2940] pb-4">
                <span className="text-xs font-bold text-[#E9DFCE] uppercase">Answer Mode:</span>
                <TrustBadge state={activeSearchMode === "ANSWERABLE" ? "CONFIRMED" : activeSearchMode === "CONFLICTING" ? "CONFLICTING" : "UNKNOWN"} />
              </div>

              {activeSearchMode === "ANSWERABLE" && (
                <div className="p-4 rounded-xl bg-[#4A1724] border border-[#681F32] text-[#FBF8F1] text-sm leading-relaxed font-medium">
                  {mode === "DEMO"
                    ? "The launch target date is October 19th, confirmed by Rahul Sharma during the Q3 Architecture Sync to accommodate security telemetry compliance."
                    : (query ? `Results returned for query: "${query}" from workspace memory.` : "Enter a search query to search live workspace memory.")}
                </div>
              )}

              {activeSearchMode === "UNKNOWN" && (
                <div className="p-4 rounded-xl bg-rose-950/80 border border-rose-500/40 text-rose-100 text-xs space-y-1 font-medium">
                  <strong>Noted Ma'am cannot establish a reliable answer. Insufficient evidence.</strong>
                  <p className="text-rose-200/80">Our strict Hallucination Boundary forbids inventing or guessing information not grounded in authorized workspace meeting records.</p>
                </div>
              )}
            </div>
          </div>
        )}

      </main>
    </div>
  );
}
