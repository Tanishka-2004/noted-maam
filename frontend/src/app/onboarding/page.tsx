"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Navigation } from "../../components/Navigation";
import { 
  Building2, 
  ShieldCheck, 
  UploadCloud, 
  UserCheck, 
  CheckCircle2, 
  ArrowRight, 
  Lock, 
  Sparkles,
  HelpCircle
} from "lucide-react";

export default function OnboardingPage() {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [workspaceName, setWorkspaceName] = useState("Acme Product Engineering");
  const [recordingPolicy, setRecordingPolicy] = useState("COMPLIANCE_RULE");
  const [selectedProjectOption, setSelectedProjectOption] = useState("unassigned");
  const [consentPolicy, setConsentPolicy] = useState("GRANTED");

  return (
    <div className="min-h-screen bg-[#FBF8F1] text-[#4A1724] bg-mesh-warm">
      <Navigation />

      <main className="max-w-4xl mx-auto px-4 py-12 space-y-8">
        {/* Progress Stepper */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#CDBEA9] pb-6">
          <div>
            <span className="text-xs font-semibold text-[#681F32] uppercase tracking-wider block font-sans">Onboarding Setup</span>
            <h1 className="text-2xl font-bold text-[#4A1724] mt-1 font-display">Configure Workspace & Consent Governance</h1>
          </div>
          <div className="flex items-center gap-2 text-xs font-medium">
            <span className={`px-3 py-1 rounded-lg ${step === 1 ? "bg-[#681F32] text-[#FBF8F1]" : "bg-[#E9DFCE] text-[#4A1724]"}`}>1. Workspace & Policy</span>
            <span className="text-[#96546A]">→</span>
            <span className={`px-3 py-1 rounded-lg ${step === 2 ? "bg-[#681F32] text-[#FBF8F1]" : "bg-[#E9DFCE] text-[#4A1724]"}`}>2. Recording Ingestion</span>
          </div>
        </div>

        {step === 1 ? (
          <div className="space-y-8 p-8 rounded-2xl bg-[#F7F1E5] border border-[#CDBEA9] shadow-sm">
            <div>
              <label className="block text-xs font-bold text-[#4A1724] uppercase mb-2">Workspace Name</label>
              <div className="flex items-center gap-3 bg-[#FBF8F1] border border-[#CDBEA9] rounded-xl px-4 py-3 text-sm focus-within:border-[#681F32]">
                <Building2 className="w-4 h-4 text-[#681F32] shrink-0" />
                <input
                  type="text"
                  value={workspaceName}
                  onChange={(e) => setWorkspaceName(e.target.value)}
                  className="bg-transparent border-none outline-none text-[#4A1724] font-medium w-full"
                />
              </div>
            </div>

            {/* Separated Consent Status vs Recording Policy */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <label className="text-xs font-bold text-[#4A1724] uppercase flex items-center gap-2">
                  <ShieldCheck className="w-4 h-4 text-[#681F32]" />
                  <span>Workspace Recording Policy</span>
                </label>
                <span className="text-[11px] text-[#96546A]">Separated from participant consent</span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {[
                  { id: "COMPLIANCE_RULE", label: "Compliance Enforcement Rule", desc: "Automated banner & prompt required before audio recording starts." },
                  { id: "AUDIO_ONLY", label: "Audio-Only Minimal Policy", desc: "Ingests voice audio only; disables screen recording video storage." },
                  { id: "MANUAL_OVERRIDE", label: "Manual Host Override", desc: "Host explicitly triggers recording after verbal confirmation." },
                  { id: "STOP", label: "Strict Consent Stop Policy", desc: "Halts recording immediately if any external participant declines consent." },
                ].map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => setRecordingPolicy(item.id)}
                    className={`text-left p-4 rounded-xl border transition-all ${
                      recordingPolicy === item.id
                        ? "bg-[#681F32] text-[#FBF8F1] border-[#681F32] shadow-sm"
                        : "bg-[#FBF8F1] border-[#CDBEA9] text-[#4A1724] hover:bg-[#E9DFCE]"
                    }`}
                  >
                    <div className="font-bold text-xs flex items-center justify-between">
                      <span>{item.label}</span>
                      {recordingPolicy === item.id && <CheckCircle2 className="w-4 h-4 text-[#FBF8F1]" />}
                    </div>
                    <p className={`text-[11px] mt-1 ${recordingPolicy === item.id ? "text-[#FBF8F1]/80" : "text-[#96546A]"}`}>{item.desc}</p>
                  </button>
                ))}
              </div>
            </div>

            {/* Consent Status Model */}
            <div className="p-4 rounded-xl bg-[#FBF8F1] border border-[#CDBEA9] space-y-3">
              <label className="text-xs font-bold text-[#4A1724] uppercase block">Default External Participant Consent Status</label>
              <div className="flex flex-wrap gap-3">
                {["GRANTED", "DECLINED", "WITHDRAWN", "UNKNOWN"].map((status) => (
                  <button
                    key={status}
                    type="button"
                    onClick={() => setConsentPolicy(status)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all ${
                      consentPolicy === status
                        ? "bg-[#681F32] text-[#FBF8F1] border-[#681F32]"
                        : "bg-[#E9DFCE] text-[#4A1724] border-[#CDBEA9]"
                    }`}
                  >
                    {status}
                  </button>
                ))}
              </div>
            </div>

            <div className="flex justify-end pt-2">
              <button
                onClick={() => setStep(2)}
                className="px-6 py-3 rounded-xl bg-[#681F32] hover:bg-[#4A1724] text-[#FBF8F1] font-semibold text-xs flex items-center gap-2 transition-all shadow-md"
              >
                <span>Continue to Ingestion Setup</span>
                <ArrowRight className="w-4 h-4 text-[#FBF8F1]" />
              </button>
            </div>
          </div>
        ) : (
          <div className="space-y-8 p-8 rounded-2xl bg-[#F7F1E5] border border-[#CDBEA9] shadow-sm">
            <div>
              <h2 className="text-sm font-bold text-[#4A1724] uppercase mb-2">Meeting Assignment Mode</h2>
              <p className="text-xs text-[#96546A] mb-4">Support uploading meeting recordings before assigning a primary project (Unassigned Inbox State).</p>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <button
                  type="button"
                  onClick={() => setSelectedProjectOption("unassigned")}
                  className={`p-5 rounded-xl border text-left transition-all ${
                    selectedProjectOption === "unassigned"
                      ? "bg-[#E9DFCE] border-[#681F32] text-[#4A1724]"
                      : "bg-[#FBF8F1] border-[#CDBEA9] text-[#4A1724]"
                  }`}
                >
                  <div className="font-bold text-xs text-[#681F32] flex items-center justify-between">
                    <span>Unassigned / Inbox State</span>
                    <span className="text-[10px] font-semibold bg-[#681F32]/10 text-[#681F32] px-2 py-0.5 rounded">primary_project_id = null</span>
                  </div>
                  <p className="text-[11px] text-[#96546A] mt-2">
                    Upload audio first. Extracted actions and decisions will wait in the global inbox until assigned to a project.
                  </p>
                </button>

                <button
                  type="button"
                  onClick={() => setSelectedProjectOption("assigned")}
                  className={`p-5 rounded-xl border text-left transition-all ${
                    selectedProjectOption === "assigned"
                      ? "bg-[#681F32] border-[#681F32] text-[#FBF8F1]"
                      : "bg-[#FBF8F1] border-[#CDBEA9] text-[#4A1724]"
                  }`}
                >
                  <div className={`font-bold text-xs flex items-center justify-between ${selectedProjectOption === "assigned" ? "text-[#FBF8F1]" : "text-[#681F32]"}`}>
                    <span>Direct Project Assignment</span>
                    <span className={`text-[10px] font-semibold px-2 py-0.5 rounded ${selectedProjectOption === "assigned" ? "bg-[#FBF8F1]/20 text-[#FBF8F1]" : "bg-[#681F32]/10 text-[#681F32]"}`}>Project Alpha</span>
                  </div>
                  <p className={`text-[11px] mt-2 ${selectedProjectOption === "assigned" ? "text-[#FBF8F1]/80" : "text-[#96546A]"}`}>
                    Immediately bind meeting recording to Project Alpha and index against project memory.
                  </p>
                </button>
              </div>
            </div>

            <div className="p-6 rounded-xl border border-dashed border-[#CDBEA9] bg-[#FBF8F1] text-center space-y-3">
              <UploadCloud className="w-8 h-8 text-[#681F32] mx-auto" />
              <div>
                <span className="text-xs font-bold text-[#4A1724] block">Drop audio recording (MP3, WAV, M4A)</span>
                <span className="text-[11px] text-[#96546A]">Simulates real-time STT, diarization & action extraction pipeline</span>
              </div>
              <button
                onClick={() => router.push("/app/meetings/demo-meeting-1")}
                className="px-4 py-2 rounded-lg bg-[#E9DFCE] border border-[#CDBEA9] text-[#4A1724] text-xs font-semibold hover:bg-[#CDBEA9] transition-all"
              >
                Load Sample Meeting ("Engineering Sync")
              </button>
            </div>

            <div className="flex justify-between items-center pt-4 border-t border-[#CDBEA9]">
              <button
                onClick={() => setStep(1)}
                className="px-4 py-2 text-xs font-medium text-[#96546A] hover:text-[#4A1724]"
              >
                Back
              </button>
              <button
                onClick={() => router.push("/app/home")}
                className="px-6 py-3 rounded-xl bg-[#681F32] hover:bg-[#4A1724] text-[#FBF8F1] font-semibold text-xs flex items-center gap-2 transition-all shadow-md"
              >
                <span>Complete Setup & Launch Home</span>
                <ArrowRight className="w-4 h-4 text-[#FBF8F1]" />
              </button>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
