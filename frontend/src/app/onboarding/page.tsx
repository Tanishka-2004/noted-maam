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
    <div className="min-h-screen bg-[#0B0F19] text-gray-100 bg-mesh-dark">
      <Navigation />

      <main className="max-w-4xl mx-auto px-4 py-12">
        {/* Progress Stepper */}
        <div className="flex items-center justify-between mb-10 border-b border-white/10 pb-6">
          <div>
            <span className="text-xs font-mono font-semibold text-emerald-400 uppercase tracking-wider">Onboarding Setup</span>
            <h1 className="text-2xl font-bold text-white mt-1">Configure Workspace & Consent Governance</h1>
          </div>
          <div className="flex items-center gap-2 text-xs font-mono">
            <span className={`px-2.5 py-1 rounded-md ${step === 1 ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30" : "text-gray-500"}`}>1. Workspace & Policy</span>
            <span className="text-gray-600">→</span>
            <span className={`px-2.5 py-1 rounded-md ${step === 2 ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30" : "text-gray-500"}`}>2. Recording Ingestion</span>
          </div>
        </div>

        {step === 1 ? (
          <div className="space-y-8 glass-panel p-8 rounded-2xl border border-white/10">
            <div>
              <label className="block text-xs font-bold text-gray-300 uppercase mb-2">Workspace Name</label>
              <div className="flex items-center gap-3 bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm focus-within:border-emerald-500">
                <Building2 className="w-4 h-4 text-emerald-400 shrink-0" />
                <input
                  type="text"
                  value={workspaceName}
                  onChange={(e) => setWorkspaceName(e.target.value)}
                  className="bg-transparent border-none outline-none text-white w-full"
                />
              </div>
            </div>

            {/* Separated Consent Status vs Recording Policy */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <label className="text-xs font-bold text-gray-300 uppercase flex items-center gap-2">
                  <ShieldCheck className="w-4 h-4 text-emerald-400" />
                  <span>Workspace Recording Policy</span>
                </label>
                <span className="text-[11px] text-gray-400 font-mono">Separated from participant consent</span>
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
                        ? "bg-emerald-500/10 border-emerald-500 text-white shadow-md shadow-emerald-950/40"
                        : "bg-white/5 border-white/10 text-gray-400 hover:border-white/20"
                    }`}
                  >
                    <div className="font-bold text-xs flex items-center justify-between">
                      <span>{item.label}</span>
                      {recordingPolicy === item.id && <CheckCircle2 className="w-4 h-4 text-emerald-400" />}
                    </div>
                    <p className="text-[11px] text-gray-400 mt-1">{item.desc}</p>
                  </button>
                ))}
              </div>
            </div>

            {/* Consent Status Model */}
            <div className="p-4 rounded-xl bg-white/5 border border-white/10 space-y-3">
              <label className="text-xs font-bold text-gray-300 uppercase block">Default External Participant Consent Status</label>
              <div className="flex flex-wrap gap-3">
                {["GRANTED", "DECLINED", "WITHDRAWN", "UNKNOWN"].map((status) => (
                  <button
                    key={status}
                    type="button"
                    onClick={() => setConsentPolicy(status)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-mono font-semibold border transition-all ${
                      consentPolicy === status
                        ? "bg-emerald-500/20 text-emerald-300 border-emerald-500"
                        : "bg-white/5 text-gray-400 border-white/10"
                    }`}
                  >
                    {status}
                  </button>
                ))}
              </div>
            </div>

            <div className="flex justify-end">
              <button
                onClick={() => setStep(2)}
                className="px-6 py-3 rounded-xl bg-gradient-to-r from-emerald-600 to-olive-600 text-white font-semibold text-xs flex items-center gap-2 hover:opacity-90 transition-opacity"
              >
                <span>Continue to Ingestion Setup</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        ) : (
          <div className="space-y-8 glass-panel p-8 rounded-2xl border border-white/10">
            <div>
              <h2 className="text-sm font-bold text-gray-200 uppercase mb-2">Meeting Assignment Mode</h2>
              <p className="text-xs text-gray-400 mb-4">Support uploading meeting recordings before assigning a primary project (Unassigned Inbox State).</p>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <button
                  type="button"
                  onClick={() => setSelectedProjectOption("unassigned")}
                  className={`p-5 rounded-xl border text-left transition-all ${
                    selectedProjectOption === "unassigned"
                      ? "bg-amber-500/10 border-amber-500 text-white"
                      : "bg-white/5 border-white/10 text-gray-400"
                  }`}
                >
                  <div className="font-bold text-xs text-amber-300 flex items-center justify-between">
                    <span>Unassigned / Inbox State</span>
                    <span className="text-[10px] font-mono bg-amber-500/20 text-amber-300 px-2 py-0.5 rounded">primary_project_id = null</span>
                  </div>
                  <p className="text-[11px] text-gray-400 mt-2">
                    Upload audio first. Extracted actions and decisions will wait in the global inbox until assigned to a project.
                  </p>
                </button>

                <button
                  type="button"
                  onClick={() => setSelectedProjectOption("assigned")}
                  className={`p-5 rounded-xl border text-left transition-all ${
                    selectedProjectOption === "assigned"
                      ? "bg-emerald-500/10 border-emerald-500 text-white"
                      : "bg-white/5 border-white/10 text-gray-400"
                  }`}
                >
                  <div className="font-bold text-xs text-emerald-300 flex items-center justify-between">
                    <span>Direct Project Assignment</span>
                    <span className="text-[10px] font-mono bg-emerald-500/20 text-emerald-300 px-2 py-0.5 rounded">Project Alpha</span>
                  </div>
                  <p className="text-[11px] text-gray-400 mt-2">
                    Immediately bind meeting recording to Project Alpha and index against project memory.
                  </p>
                </button>
              </div>
            </div>

            <div className="p-6 rounded-xl border border-dashed border-white/20 bg-white/5 text-center space-y-3">
              <UploadCloud className="w-8 h-8 text-emerald-400 mx-auto" />
              <div>
                <span className="text-xs font-bold text-white block">Drop audio recording (MP3, WAV, M4A)</span>
                <span className="text-[11px] text-gray-400">Simulates real-time STT, diarization & action extraction pipeline</span>
              </div>
              <button
                onClick={() => router.push("/meetings/demo-meeting-1")}
                className="px-4 py-2 rounded-lg bg-emerald-500/20 border border-emerald-500/30 text-emerald-300 text-xs font-semibold hover:bg-emerald-500/30 transition-all"
              >
                Load Sample Meeting ("Engineering Sync")
              </button>
            </div>

            <div className="flex justify-between items-center pt-4">
              <button
                onClick={() => setStep(1)}
                className="px-4 py-2 text-xs font-medium text-gray-400 hover:text-white"
              >
                Back
              </button>
              <button
                onClick={() => router.push("/command-center")}
                className="px-6 py-3 rounded-xl bg-gradient-to-r from-emerald-600 to-olive-600 text-white font-semibold text-xs flex items-center gap-2 hover:opacity-90 transition-opacity"
              >
                <span>Complete Setup & Launch Command Center</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
