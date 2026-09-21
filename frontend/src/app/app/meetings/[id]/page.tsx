"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { Navigation } from "../../../../components/Navigation";
import { TrustBadge } from "../../../../components/TrustBadge";
import { ProvenanceDrawer, ProvenanceData } from "../../../../components/ProvenanceDrawer";
import { 
  Play, 
  Pause, 
  Clock, 
  Check, 
  X, 
  Sparkles, 
  ShieldCheck, 
  FileText, 
  Users, 
  Volume2, 
  ArrowLeft,
  ChevronRight,
  RotateCcw,
  HelpCircle
} from "lucide-react";

export default function AppMeetingDetailPage() {
  const params = useParams();
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState("32:18");
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [confirmedTasks, setConfirmedTasks] = useState<Record<string, boolean>>({});
  const [activeProvenance, setActiveProvenance] = useState<ProvenanceData | null>(null);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3000);
  };

  const toggleConfirm = (taskId: string, title: string) => {
    const nextState = !confirmedTasks[taskId];
    setConfirmedTasks(prev => ({ ...prev, [taskId]: nextState }));
    if (nextState) {
      showToast(`Task confirmed: "${title.slice(0, 30)}..."`);
    } else {
      showToast(`Reverted to SUGGESTED: "${title.slice(0, 30)}..."`);
    }
  };

  const handlePlayAudioFrom = (timestamp: string) => {
    setCurrentTime(timestamp);
    setIsPlaying(true);
    showToast(`Seeking audio playback to ${timestamp}`);
  };

  const utterances = [
    {
      id: "seg_181",
      speaker: "Rohan Varma",
      speakerTag: "SPEAKER_01",
      timestamp: "32:10",
      timeRange: "32:10-32:17",
      text: "We need to ensure all auth endpoints adhere to strict OpenAPI schemas before the launch.",
      confidence: "98%"
    },
    {
      id: "seg_182",
      speaker: "Rohan Varma",
      speakerTag: "SPEAKER_01",
      timestamp: "32:18",
      timeRange: "32:18-32:25",
      text: "I'll get the API contract finalized by Friday afternoon so Aarohi can start testing.",
      confidence: "99%",
      extractedTask: {
        id: "task_api_contract",
        title: "Finalize OpenAPI contract endpoints by Friday afternoon",
        owner: "Rohan Varma",
        deadline: "Friday 17:00 UTC",
        priority: "High",
        provenance: {
          title: "Finalize OpenAPI contract endpoints by Friday afternoon",
          sourceMeeting: "Q3 Engineering Architecture Sync",
          timestamp: "32:18",
          timeRange: "32:18-32:25",
          speaker: "Rohan Varma",
          speakerTag: "SPEAKER_01",
          quote: "I'll get the API contract finalized by Friday afternoon so Aarohi can start testing.",
          confidence: "99%",
          extractorVersion: "actions-v3.1",
          reason: "Rohan committed to completing OpenAPI contracts by Friday.",
          trustState: "CONFIRMED" as const
        }
      }
    },
    {
      id: "seg_183",
      speaker: "Aarohi Sharma",
      speakerTag: "SPEAKER_02",
      timestamp: "32:26",
      timeRange: "32:26-32:34",
      text: "Sounds good Rohan. Once that is done, I will run full regression tests on test_iam DB.",
      confidence: "96%"
    },
    {
      id: "seg_184",
      speaker: "Rahul Sharma",
      speakerTag: "SPEAKER_00",
      timestamp: "32:35",
      timeRange: "32:35-32:45",
      text: "Confirmed. Launch target date is locked for October 19th pending telemetry signoff.",
      confidence: "97%",
      extractedDecision: {
        id: "dec_launch_date",
        summary: "Launch target date set to October 19th",
        rationale: "Aligns with client onboarding window after telemetry review."
      }
    }
  ];

  return (
    <div className="min-h-screen bg-[#4A1724] text-[#FBF8F1] pb-16 font-sans">
      <Navigation />
      <ProvenanceDrawer 
        data={activeProvenance} 
        onClose={() => setActiveProvenance(null)} 
        onPlayAudio={handlePlayAudioFrom}
      />

      {/* Toast */}
      {toastMessage && (
        <div className="fixed bottom-6 right-6 z-50 bg-[#FBF8F1] text-[#4A1724] px-5 py-3 rounded-xl shadow-2xl flex items-center gap-2 text-xs font-bold animate-bounce">
          <Sparkles className="w-4 h-4 text-[#4A1724]" />
          <span>{toastMessage}</span>
        </div>
      )}

      <main className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 pt-6 space-y-6">
        
        {/* Back Link & Header */}
        <div className="flex items-center justify-between">
          <Link href="/app/meetings" className="text-xs text-[#E9DFCE] hover:text-[#FBF8F1] flex items-center gap-1 font-medium">
            <ArrowLeft className="w-4 h-4" />
            <span>Back to Meetings</span>
          </Link>
          <div className="flex items-center gap-2 text-xs font-semibold text-[#FBF8F1]">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            <span>Outcome Verification Mode Active</span>
          </div>
        </div>

        {/* Meeting Overview & Audio Deck */}
        <div className="p-6 rounded-2xl bg-[#5C1D2D] border border-[#7A2940] space-y-4 shadow-md">
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
            <div>
              <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-[#FBF8F1] text-[#4A1724]">
                Primary Project: Project Alpha
              </span>
              <h1 className="text-2xl font-extrabold text-[#FBF8F1] mt-1 font-display">Q3 Engineering Architecture & Auth Gateway Sync</h1>
              <p className="text-xs text-[#E9DFCE] mt-0.5 font-medium">Recorded 2026-07-10 • Duration 42m 18s • 4 Speakers Diarized</p>
            </div>

            {/* Audio Player Controls */}
            <div className="flex items-center gap-4 bg-[#4A1724] p-3 rounded-xl border border-[#681F32]">
              <button
                onClick={() => setIsPlaying(!isPlaying)}
                className="w-10 h-10 rounded-full bg-[#FBF8F1] hover:bg-[#F7F1E5] text-[#4A1724] flex items-center justify-center shadow-md transition-transform hover:scale-105"
              >
                {isPlaying ? <Pause className="w-5 h-5 fill-[#4A1724]" /> : <Play className="w-5 h-5 fill-[#4A1724] ml-0.5" />}
              </button>
              <div>
                <span className="text-xs font-bold text-[#FBF8F1] block">{currentTime} / 42:18</span>
                <span className="text-[10px] text-[#E9DFCE] font-medium">Audio Stream: verified_320kbps</span>
              </div>
              <Volume2 className="w-4 h-4 text-[#E9DFCE] ml-2" />
            </div>
          </div>
        </div>

        {/* OUTCOME-FIRST HIERARCHY */}
        <div className="space-y-6">
          
          {/* SECTION 1: WHAT HAPPENED */}
          <div className="p-6 rounded-2xl bg-[#5C1D2D] border border-[#7A2940] space-y-2 shadow-md">
            <h2 className="text-xs font-bold text-[#FBF8F1] uppercase tracking-wider font-sans">WHAT HAPPENED</h2>
            <p className="text-sm text-[#FBF8F1] leading-relaxed font-medium">
              Launch target date locked for October 19th pending telemetry compliance testing. Rohan committed to completing OpenAPI auth gateway specifications by Friday afternoon.
            </p>
          </div>

          {/* SECTION 2: ACTION ITEMS */}
          <div className="p-6 rounded-2xl bg-[#5C1D2D] border border-[#7A2940] space-y-4 shadow-md">
            <div className="flex items-center justify-between border-b border-[#7A2940] pb-3">
              <h2 className="text-xs font-bold text-[#FBF8F1] uppercase tracking-wider font-sans">ACTION ITEMS (AI PROPOSALS)</h2>
              <span className="text-[11px] text-[#E9DFCE] font-medium">Click Inspector for Provenance</span>
            </div>

            {utterances.filter(u => u.extractedTask).map((u) => {
              const task = u.extractedTask!;
              const isConfirmed = confirmedTasks[task.id];
              return (
                <div key={task.id} className="p-4 rounded-xl bg-[#4A1724] border border-[#681F32] space-y-3">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <TrustBadge state={isConfirmed ? "CONFIRMED" : "CONFIRMED"} customLabel={isConfirmed ? "CONFIRMED · Human verified" : "PROPOSED"} />
                        <span className="text-xs text-[#E9DFCE]">Assignee: <strong className="text-[#FBF8F1]">{task.owner}</strong></span>
                      </div>
                      <h3 className="font-bold text-sm text-[#FBF8F1]">{task.title}</h3>
                    </div>

                    <button
                      onClick={() => setActiveProvenance(task.provenance)}
                      className="px-3 py-1.5 rounded-lg border border-[#7A2940] bg-[#681F32] text-[#FBF8F1] text-xs font-semibold hover:bg-[#7A2940] flex items-center gap-1 shrink-0"
                    >
                      <HelpCircle className="w-3.5 h-3.5 text-[#FBF8F1]" />
                      <span>Why am I seeing this?</span>
                    </button>
                  </div>

                  <div className="p-3 rounded-lg bg-[#5C1D2D] border border-[#7A2940] text-xs text-[#FBF8F1] flex items-center justify-between font-medium">
                    <span className="italic">"{u.text}"</span>
                    <button 
                      onClick={() => handlePlayAudioFrom(u.timestamp)}
                      className="text-[11px] text-[#E9DFCE] font-bold hover:underline flex items-center gap-1 shrink-0 ml-2"
                    >
                      <Play className="w-3 h-3 fill-[#E9DFCE]" />
                      <span>{u.timestamp}</span>
                    </button>
                  </div>

                  {/* Confirm Action Button */}
                  <div className="flex justify-end pt-1">
                    {isConfirmed ? (
                      <button
                        onClick={() => toggleConfirm(task.id, task.title)}
                        className="px-4 py-2 rounded-xl border border-[#7A2940] bg-[#681F32] text-[#FBF8F1] text-xs font-semibold flex items-center gap-1.5"
                      >
                        <RotateCcw className="w-3.5 h-3.5" />
                        <span>Undo Confirmation</span>
                      </button>
                    ) : (
                      <button
                        onClick={() => toggleConfirm(task.id, task.title)}
                        className="px-4 py-2 rounded-xl bg-[#FBF8F1] hover:bg-[#F7F1E5] text-[#4A1724] text-xs font-bold shadow-md flex items-center gap-1.5"
                      >
                        <Check className="w-3.5 h-3.5 text-[#4A1724]" />
                        <span>Confirm & Assign Commitment</span>
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {/* SECTION 3: DECISIONS */}
          <div className="p-6 rounded-2xl bg-[#5C1D2D] border border-[#7A2940] space-y-3 shadow-md">
            <h2 className="text-xs font-bold text-[#FBF8F1] uppercase tracking-wider font-sans">CONFIRMED DECISIONS</h2>

            {utterances.filter(u => u.extractedDecision).map((u) => {
              const dec = u.extractedDecision!;
              return (
                <div key={dec.id} className="p-4 rounded-xl bg-[#4A1724] border border-[#681F32] space-y-1.5">
                  <TrustBadge state="CONFIRMED" customLabel="CONFIRMED DECISION" />
                  <h3 className="font-bold text-sm text-[#FBF8F1] mt-1">{dec.summary}</h3>
                  <p className="text-xs text-[#E9DFCE] font-medium">{dec.rationale}</p>
                  <div className="text-[11px] text-[#E9DFCE] pt-1 font-medium">
                    Evidence quote at {u.timestamp}: "{u.text}"
                  </div>
                </div>
              );
            })}
          </div>

          {/* SECTION 4: TRANSCRIPT (COLLAPSIBLE / SECONDARY) */}
          <details className="p-6 rounded-2xl bg-[#5C1D2D] border border-[#7A2940] space-y-4 shadow-md">
            <summary className="text-xs font-bold text-[#FBF8F1] uppercase tracking-wider font-sans cursor-pointer hover:underline flex items-center justify-between">
              <span>FULL TRANSCRIPT & DIARIZATION (SECONDARY)</span>
              <span className="text-[11px] text-[#E9DFCE]">Click to Expand (4 utterances)</span>
            </summary>

            <div className="space-y-3 pt-4 border-t border-[#7A2940]">
              {utterances.map((u) => (
                <div key={u.id} className="p-4 rounded-xl bg-[#4A1724] border border-[#681F32] space-y-1 font-medium">
                  <div className="flex justify-between text-xs">
                    <span className="font-bold text-[#FBF8F1]">{u.speaker}</span>
                    <button onClick={() => handlePlayAudioFrom(u.timestamp)} className="text-[#E9DFCE] hover:underline">
                      {u.timestamp}
                    </button>
                  </div>
                  <p className="text-xs text-[#FBF8F1]">{u.text}</p>
                </div>
              ))}
            </div>
          </details>

        </div>
      </main>
    </div>
  );
}
