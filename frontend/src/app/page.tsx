"use client";

import React from "react";
import Link from "next/link";
import { Navigation } from "../components/Navigation";
import { DemoModeBanner } from "../components/DemoModeBanner";
import { 
  Sparkles, 
  ArrowRight, 
  ShieldCheck, 
  Activity, 
  GitCommit, 
  CheckSquare, 
  Search, 
  Lock, 
  Workflow,
  Play,
  Database,
  RefreshCw,
  Users
} from "lucide-react";

export default function LandingPage() {
  const sixPartLoop = [
    { title: "1. Capture", desc: "Multilingual audio & meeting transcript ingestion with speaker diarization." },
    { title: "2. Understand", desc: "Extract commitments, decisions, and conflicts using Whisper & GPT-4o." },
    { title: "3. Verify", desc: "Human evidence gate: 'AI proposes, humans decide' before updating reality." },
    { title: "4. Execute", desc: "Idempotent 2-way sync into Jira, Slack, and Linear with version tracking." },
    { title: "5. Remember", desc: "Permission-gated vector index with immutable transcript citation links." },
    { title: "6. Detect Change", desc: "Project Pulse and Decision Lineage tree showing how organizational reality evolved." },
  ];

  return (
    <div className="min-h-screen bg-[#FBF8F1] text-[#4A1724] bg-mesh-warm selection:bg-[#681F32] selection:text-[#FBF8F1]">
      <DemoModeBanner />
      <Navigation />

      {/* Hero Section */}
      <section className="relative pt-16 pb-20 px-4 sm:px-6 lg:px-8 max-w-6xl mx-auto text-center">
        <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[#E9DFCE] border border-[#CDBEA9] text-[#681F32] text-xs font-mono font-bold mb-8 animate-pulse-subtle">
          <Sparkles className="w-3.5 h-3.5 text-[#681F32]" />
          <span>Burgundy & Cream Editorial Visual Identity</span>
        </div>

        <h1 className="text-4xl sm:text-6xl font-extrabold tracking-tight text-[#4A1724] max-w-4xl mx-auto leading-tight font-display">
          Turn conversations into <span className="text-[#681F32] underline decoration-[#96546A]">verified decisions</span>, accountable commitments, and searchable project memory.
        </h1>

        <p className="mt-6 text-lg sm:text-xl text-[#96546A] max-w-3xl mx-auto font-medium leading-relaxed">
          Meetings create information, but teams lose context. Noted Ma'am goes beyond simple transcription into evidence-backed verification, supersession tracking, and project change detection.
        </p>

        {/* Hero Action Buttons */}
        <div className="mt-10 flex flex-wrap items-center justify-center gap-4">
          <Link
            href="/app/home"
            className="px-7 py-3.5 rounded-xl bg-[#681F32] hover:bg-[#4A1724] text-[#FBF8F1] font-semibold text-sm transition-all flex items-center gap-2 shadow-xl hover:scale-[1.02]"
          >
            <span>Launch Executive Command Center</span>
            <ArrowRight className="w-4 h-4 text-[#FBF8F1]" />
          </Link>
          <Link
            href="/onboarding"
            className="px-6 py-3.5 rounded-xl bg-[#E9DFCE] hover:bg-[#CDBEA9] text-[#4A1724] font-semibold text-sm transition-all border border-[#CDBEA9] flex items-center gap-2"
          >
            <Users className="w-4 h-4 text-[#681F32]" />
            <span>Interactive Onboarding</span>
          </Link>
        </div>

        {/* Governing Principle Banner */}
        <div className="mt-12 max-w-2xl mx-auto p-5 rounded-xl bg-[#F7F1E5] border border-[#CDBEA9] text-left flex items-start gap-3 shadow-sm">
          <Lock className="w-5 h-5 text-[#681F32] shrink-0 mt-0.5" />
          <div>
            <span className="text-xs font-bold text-[#681F32] uppercase tracking-wide block font-mono">Core Governance Principle</span>
            <p className="text-xs text-[#4A1724] mt-0.5 leading-normal">
              <strong>"AI proposes, humans decide."</strong> Noted Ma'am detects signals and quotes evidence, but cannot silently alter project commitments or legal decisions without explicit human verification.
            </p>
          </div>
        </div>
      </section>

      {/* Six-Part Operating Loop */}
      <section className="py-16 px-4 sm:px-6 lg:px-8 max-w-6xl mx-auto border-t border-[#CDBEA9]">
        <div className="text-center mb-12">
          <h2 className="text-2xl sm:text-3xl font-bold text-[#4A1724]">The Six-Part Product Backbone</h2>
          <p className="text-xs sm:text-sm text-[#96546A] mt-2 font-medium">The complete operational cycle transforming audio into verified organizational reality.</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {sixPartLoop.map((item, i) => (
            <div key={i} className="p-6 rounded-2xl bg-[#F7F1E5] border border-[#CDBEA9] hover:border-[#7A2940] transition-all space-y-2">
              <h3 className="font-bold text-sm text-[#681F32]">{item.title}</h3>
              <p className="text-xs text-[#4A1724] leading-relaxed">{item.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Footer */}
      <footer className="py-8 border-t border-[#CDBEA9] text-center text-xs text-[#96546A] font-mono">
        <p>Noted Ma'am — Burgundy & Cream Visual System — Editorial B2B Product Architecture</p>
      </footer>
    </div>
  );
}
