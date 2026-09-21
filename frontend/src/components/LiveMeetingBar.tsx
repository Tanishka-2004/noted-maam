"use client";

import React from "react";
import { useLiveMeeting } from "../context/LiveMeetingContext";
import { Mic, Pause, Play, Square, Maximize2, Sparkles, Activity } from "lucide-react";

export function LiveMeetingBar() {
  const { 
    isRecording, 
    isPaused, 
    elapsedSeconds, 
    meetingTitle, 
    extractedItems, 
    pauseMeeting, 
    resumeMeeting, 
    endMeeting, 
    openModal 
  } = useLiveMeeting();

  if (!isRecording) return null;

  const formatTime = (secs: number) => {
    const mins = Math.floor(secs / 60).toString().padStart(2, "0");
    const s = (secs % 60).toString().padStart(2, "0");
    return `${mins}:${s}`;
  };

  return (
    <div className="fixed bottom-6 right-6 z-50 max-w-xl w-full sm:w-auto bg-[#5C1D2D] text-[#FBF8F1] border-2 border-[#7A2940] rounded-2xl p-4 shadow-2xl backdrop-blur-xl animate-slide-up flex flex-col sm:flex-row items-center justify-between gap-4 font-sans">
      
      {/* Left Group: Recording Indicator + Live Timer + Title */}
      <div className="flex items-center gap-3 w-full sm:w-auto">
        <div className="relative flex items-center justify-center">
          <div className={`w-3.5 h-3.5 rounded-full ${isPaused ? "bg-amber-400" : "bg-rose-500 animate-ping"}`} />
          <div className={`absolute w-3.5 h-3.5 rounded-full ${isPaused ? "bg-amber-400" : "bg-rose-500"}`} />
        </div>

        <div>
          <div className="flex items-center gap-2 text-xs font-bold text-[#FBF8F1]">
            <span className="font-mono bg-[#4A1724] border border-[#7A2940] px-2 py-0.5 rounded text-[11px]">
              {formatTime(elapsedSeconds)}
            </span>
            <span className="truncate max-w-[180px] sm:max-w-[220px] font-display">{meetingTitle}</span>
          </div>
          <div className="text-[11px] text-[#E9DFCE] font-medium flex items-center gap-1.5 mt-0.5">
            <Sparkles className="w-3 h-3 text-[#FBF8F1]" />
            <span>AI Live Extraction: <strong>{extractedItems.length} items detected</strong></span>
          </div>
        </div>
      </div>

      {/* Action Controls */}
      <div className="flex items-center gap-2 shrink-0 w-full sm:w-auto justify-end border-t sm:border-t-0 border-[#7A2940] pt-2 sm:pt-0">
        <button
          onClick={openModal}
          className="px-3 py-1.5 rounded-xl bg-[#4A1724] hover:bg-[#681F32] border border-[#7A2940] text-xs font-bold text-[#FBF8F1] flex items-center gap-1.5 transition-all"
        >
          <Maximize2 className="w-3 h-3 text-[#FBF8F1]" />
          <span>Control Room</span>
        </button>

        {isPaused ? (
          <button
            onClick={resumeMeeting}
            className="p-2 rounded-xl bg-[#681F32] hover:bg-[#7A2940] border border-[#7A2940] text-[#FBF8F1] text-xs font-bold"
            title="Resume Live Meeting"
          >
            <Play className="w-3.5 h-3.5 text-[#FBF8F1]" />
          </button>
        ) : (
          <button
            onClick={pauseMeeting}
            className="p-2 rounded-xl bg-[#681F32] hover:bg-[#7A2940] border border-[#7A2940] text-[#FBF8F1] text-xs font-bold"
            title="Pause Live Meeting"
          >
            <Pause className="w-3.5 h-3.5 text-[#FBF8F1]" />
          </button>
        )}

        <button
          onClick={endMeeting}
          className="px-3 py-1.5 rounded-xl bg-[#FBF8F1] hover:bg-[#F7F1E5] text-[#4A1724] font-bold text-xs flex items-center gap-1.5 shadow-md transition-all"
        >
          <Square className="w-3 h-3 text-[#4A1724] fill-current" />
          <span>End & Save</span>
        </button>
      </div>

    </div>
  );
}
