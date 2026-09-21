"use client";

import React, { useRef, useEffect } from "react";
import { useLiveMeeting } from "../context/LiveMeetingContext";
import { TrustBadge } from "./TrustBadge";
import { 
  X, 
  Mic, 
  Pause, 
  Play, 
  Square, 
  ShieldCheck, 
  Sparkles, 
  Activity, 
  FileText, 
  CheckCircle2, 
  AlertTriangle,
  FolderPlus
} from "lucide-react";

export function LiveMeetingModal() {
  const { 
    isRecording, 
    isPaused, 
    isModalOpen, 
    elapsedSeconds, 
    meetingTitle, 
    selectedProject, 
    audioSourceMode,
    transcript, 
    extractedItems, 
    pauseMeeting, 
    resumeMeeting, 
    endMeeting, 
    closeModal,
    setAudioSourceMode,
    setSelectedProject,
    setMeetingTitle 
  } = useLiveMeeting();

  const transcriptEndRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (transcriptEndRef.current) {
      transcriptEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [transcript]);

  if (!isModalOpen) return null;

  const formatTime = (secs: number) => {
    const mins = Math.floor(secs / 60).toString().padStart(2, "0");
    const s = (secs % 60).toString().padStart(2, "0");
    return `${mins}:${s}`;
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-md flex items-center justify-center p-4 font-sans">
      <div className="max-w-5xl w-full bg-[#4A1724] border-2 border-[#7A2940] rounded-3xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        
        {/* Header */}
        <div className="p-6 bg-[#5C1D2D] border-b border-[#7A2940] flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-[#4A1724] border border-[#7A2940] flex items-center justify-center">
              <Mic className="w-5 h-5 text-rose-400 animate-pulse" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-extrabold uppercase px-2.5 py-0.5 rounded-full bg-rose-500/20 text-rose-300 border border-rose-500/40 tracking-wider">
                  LIVE BACKGROUND INGESTION
                </span>
                <span className="text-xs font-mono font-bold text-[#FBF8F1] bg-[#4A1724] px-2 py-0.5 rounded border border-[#7A2940]">
                  {formatTime(elapsedSeconds)}
                </span>
              </div>
              <input
                type="text"
                value={meetingTitle}
                onChange={(e) => setMeetingTitle(e.target.value)}
                className="bg-transparent text-lg font-extrabold text-[#FBF8F1] outline-none border-b border-transparent focus:border-[#FBF8F1] font-display mt-0.5 w-full sm:w-96"
              />
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={closeModal}
              className="p-2 rounded-xl bg-[#4A1724] hover:bg-[#681F32] border border-[#7A2940] text-[#E9DFCE] hover:text-[#FBF8F1] transition-all"
              title="Minimize to Background Bar"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Live Audio Visualizer Bar */}
        <div className="px-6 py-3 bg-[#4A1724] border-b border-[#681F32] flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <div className="flex items-end gap-1 h-5">
              <div className="w-1 bg-rose-500 rounded animate-bounce h-3" />
              <div className="w-1 bg-rose-400 rounded animate-bounce h-5 delay-75" />
              <div className="w-1 bg-amber-400 rounded animate-bounce h-2 delay-150" />
              <div className="w-1 bg-emerald-400 rounded animate-bounce h-4 delay-100" />
            </div>
            <span className="text-xs font-semibold text-[#E9DFCE]">
              {isPaused ? "Recording Paused" : "System & Mic Audio Active · Capturing headphones & room live"}
            </span>
          </div>

          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5 bg-[#5C1D2D] p-1 rounded-xl border border-[#7A2940]">
              <button
                onClick={() => setAudioSourceMode("SYSTEM_TAB_AUDIO")}
                className={`px-3 py-1 rounded-lg text-[11px] font-bold transition-all ${
                  audioSourceMode === "SYSTEM_TAB_AUDIO" 
                    ? "bg-[#FBF8F1] text-[#4A1724]" 
                    : "text-[#E9DFCE] hover:text-[#FBF8F1]"
                }`}
                title="Captures computer / Meet / Zoom tab audio directly (Required when wearing headphones)"
              >
                🎧 System/Tab Audio (Headphones)
              </button>
              <button
                onClick={() => setAudioSourceMode("MIC_ONLY")}
                className={`px-3 py-1 rounded-lg text-[11px] font-bold transition-all ${
                  audioSourceMode === "MIC_ONLY" 
                    ? "bg-[#FBF8F1] text-[#4A1724]" 
                    : "text-[#E9DFCE] hover:text-[#FBF8F1]"
                }`}
                title="Captures room microphone audio only"
              >
                🎙️ Mic Only
              </button>
            </div>

            <div className="hidden md:flex items-center gap-1.5 text-xs font-semibold text-[#E9DFCE]">
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
              <span>Consent: <strong className="text-[#FBF8F1]">COMPLIANCE_RULE</strong></span>
            </div>
          </div>
        </div>

        {/* Modal Main Body: Dual Panel (Live Transcript + Real-time AI Extraction Stream) */}
        <div className="flex-1 overflow-hidden grid grid-cols-1 lg:grid-cols-12 divide-y lg:divide-y-0 lg:divide-x divide-[#681F32]">
          
          {/* Left 7 Columns: Live Speech Transcript Feed */}
          <div className="lg:col-span-7 p-6 overflow-y-auto space-y-4">
            <div className="flex items-center justify-between border-b border-[#681F32] pb-3">
              <div className="flex items-center gap-2 text-xs font-bold text-[#FBF8F1] uppercase tracking-wider">
                <FileText className="w-4 h-4 text-[#FBF8F1]" />
                <span>Live Speech Transcript ({transcript.length} lines)</span>
              </div>
              <span className="text-[10px] text-[#E9DFCE] font-mono">Diarization Engine: Active</span>
            </div>

            {transcript.length === 0 ? (
              <div className="p-8 text-center text-xs text-[#E9DFCE] font-medium space-y-2">
                <Mic className="w-8 h-8 text-[#FBF8F1] mx-auto opacity-60 animate-pulse" />
                <p>Listening to room audio... Speak to see live transcript stream.</p>
              </div>
            ) : (
              <div className="space-y-3">
                {transcript.map((item) => (
                  <div key={item.id} className="p-3.5 rounded-xl bg-[#5C1D2D] border border-[#7A2940] space-y-1 text-xs">
                    <div className="flex items-center justify-between font-mono text-[10px]">
                      <span className="font-bold text-[#FBF8F1]">{item.speaker} ({item.speakerTag})</span>
                      <span className="text-[#E9DFCE]">{item.timestamp}</span>
                    </div>
                    <p className="text-[#FBF8F1] font-medium leading-relaxed">{item.text}</p>
                  </div>
                ))}
                <div ref={transcriptEndRef} />
              </div>
            )}
          </div>

          {/* Right 5 Columns: Real-Time AI Extraction Engine */}
          <div className="lg:col-span-5 p-6 overflow-y-auto space-y-4 bg-[#5C1D2D]/40">
            <div className="flex items-center justify-between border-b border-[#681F32] pb-3">
              <div className="flex items-center gap-2 text-xs font-bold text-[#FBF8F1] uppercase tracking-wider">
                <Sparkles className="w-4 h-4 text-[#FBF8F1]" />
                <span>Extracted Action Stream ({extractedItems.length})</span>
              </div>
            </div>

            {extractedItems.length === 0 ? (
              <div className="p-8 text-center text-xs text-[#E9DFCE] font-medium space-y-2">
                <Activity className="w-8 h-8 text-[#FBF8F1] mx-auto opacity-60" />
                <p>AI Action Extractor active. Express explicit commitments or decisions to extract live items.</p>
              </div>
            ) : (
              <div className="space-y-3">
                {extractedItems.map((item) => (
                  <div key={item.id} className="p-4 rounded-xl bg-[#4A1724] border border-[#7A2940] space-y-2 hover:border-[#FBF8F1]/40 transition-all">
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] font-extrabold px-2 py-0.5 rounded bg-[#5C1D2D] text-[#FBF8F1] border border-[#7A2940]">
                        {item.type}
                      </span>
                      <TrustBadge state={item.trustBadge} size="sm" />
                    </div>

                    <h4 className="font-bold text-xs text-[#FBF8F1]">{item.title}</h4>
                    
                    {item.assignee && (
                      <div className="text-[11px] text-[#E9DFCE] font-medium">
                        Assignee: <strong className="text-[#FBF8F1]">{item.assignee}</strong>
                      </div>
                    )}

                    <div className="text-[10px] text-[#E9DFCE] italic border-t border-[#681F32] pt-1.5 font-mono">
                      "{item.evidence}"
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

        </div>

        {/* Footer Actions */}
        <div className="p-6 bg-[#5C1D2D] border-t border-[#7A2940] flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-3 w-full sm:w-auto">
            <span className="text-xs font-semibold text-[#E9DFCE]">Assign to Project:</span>
            <select
              value={selectedProject}
              onChange={(e) => setSelectedProject(e.target.value)}
              className="bg-[#4A1724] border border-[#7A2940] text-xs font-bold text-[#FBF8F1] rounded-xl px-3 py-1.5 outline-none"
            >
              <option value="Project Alpha">Project Alpha</option>
              <option value="Project Nova">Project Nova</option>
              <option value="Unassigned Inbox">Unassigned Inbox</option>
            </select>
          </div>

          <div className="flex items-center gap-3 w-full sm:w-auto justify-end">
            {isPaused ? (
              <button
                onClick={resumeMeeting}
                className="px-4 py-2 rounded-xl bg-[#681F32] hover:bg-[#7A2940] border border-[#7A2940] text-xs font-bold text-[#FBF8F1] flex items-center gap-2"
              >
                <Play className="w-4 h-4 text-[#FBF8F1]" />
                <span>Resume Recording</span>
              </button>
            ) : (
              <button
                onClick={pauseMeeting}
                className="px-4 py-2 rounded-xl bg-[#681F32] hover:bg-[#7A2940] border border-[#7A2940] text-xs font-bold text-[#FBF8F1] flex items-center gap-2"
              >
                <Pause className="w-4 h-4 text-[#FBF8F1]" />
                <span>Pause Recording</span>
              </button>
            )}

            <button
              onClick={endMeeting}
              className="px-5 py-2 rounded-xl bg-[#FBF8F1] hover:bg-[#F7F1E5] text-[#4A1724] font-bold text-xs flex items-center gap-2 shadow-md transition-all"
            >
              <Square className="w-4 h-4 text-[#4A1724] fill-current" />
              <span>End & Finalize Meeting</span>
            </button>
          </div>
        </div>

      </div>
    </div>
  );
}
