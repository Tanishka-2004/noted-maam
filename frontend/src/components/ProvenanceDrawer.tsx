"use client";

import React from "react";
import { HelpCircle, X, Clock, FileText, Check, Play, ArrowLeft } from "lucide-react";
import { TrustBadge, TrustState } from "./TrustBadge";

export interface ProvenanceData {
  title: string;
  sourceMeeting: string;
  timestamp: string;
  timeRange: string;
  speaker: string;
  speakerTag: string;
  quote: string;
  confidence: string;
  extractorVersion: string;
  reason: string;
  trustState?: TrustState;
}

interface ProvenanceDrawerProps {
  data: ProvenanceData | null;
  onClose: () => void;
  onConfirmAction?: () => void;
  onPlayAudio?: (timestamp: string) => void;
}

export function ProvenanceDrawer({ data, onClose, onConfirmAction, onPlayAudio }: ProvenanceDrawerProps) {
  if (!data) return null;

  return (
    <div className="fixed inset-0 z-50 bg-[#4A1724]/40 backdrop-blur-sm flex justify-end animate-fade-in">
      <div className="w-full max-w-lg bg-[#F7F1E5] border-l border-[#CDBEA9] p-6 space-y-6 overflow-y-auto animate-slide-left shadow-2xl text-[#4A1724]">
        
        {/* Evidence Inspector Header */}
        <div className="flex items-center justify-between border-b border-[#CDBEA9] pb-4">
          <div className="flex items-center gap-2 text-[#681F32] font-mono text-xs font-bold uppercase tracking-wider">
            <ArrowLeft className="w-4 h-4 text-[#96546A] cursor-pointer hover:text-[#4A1724]" onClick={onClose} />
            <span>Evidence Inspector</span>
          </div>
          <button 
            onClick={onClose}
            className="text-[#96546A] hover:text-[#4A1724] p-1 rounded-lg hover:bg-[#E9DFCE] transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content Body */}
        <div className="space-y-4">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <TrustBadge state={data.trustState || "CONFIRMED"} />
            </div>
            <span className="text-[10px] font-mono text-[#96546A] uppercase font-bold block">Why this exists</span>
            <h3 className="font-bold text-base text-[#4A1724] mt-0.5">{data.title}</h3>
          </div>

          {/* Rationale Box */}
          <div className="p-4 rounded-xl bg-[#E9DFCE] border border-[#CDBEA9] space-y-1">
            <span className="text-[10px] font-bold text-[#681F32] uppercase block font-mono">Extraction Rationale</span>
            <p className="text-xs text-[#4A1724] leading-relaxed">{data.reason}</p>
          </div>

          {/* Source Meeting & Audio Seek Trigger */}
          <div className="p-4 rounded-xl bg-[#FBF8F1] border border-[#CDBEA9] space-y-3">
            <div className="flex justify-between items-center text-[10px] font-mono text-[#96546A] border-b border-[#CDBEA9]/60 pb-2">
              <span className="flex items-center gap-1 font-bold">
                <FileText className="w-3.5 h-3.5 text-[#681F32]" />
                {data.sourceMeeting}
              </span>
              <span className="text-[#681F32] font-bold flex items-center gap-1">
                <Clock className="w-3.5 h-3.5" />
                {data.timeRange}
              </span>
            </div>

            <div className="space-y-1">
              <span className="text-[10px] font-mono text-[#96546A] uppercase block">Exact Verbatim Evidence</span>
              <p className="italic text-xs text-[#4A1724] leading-relaxed bg-[#E9DFCE]/60 p-3 rounded-lg border border-[#CDBEA9]">
                "{data.quote}"
              </p>
            </div>

            {/* Audio Seek Button */}
            <button
              onClick={() => onPlayAudio && onPlayAudio(data.timestamp)}
              className="w-full py-2.5 rounded-xl bg-[#681F32] hover:bg-[#4A1724] text-[#FBF8F1] text-xs font-semibold flex items-center justify-center gap-2 transition-all shadow-md"
            >
              <Play className="w-3.5 h-3.5 fill-[#FBF8F1]" />
              <span>Play Audio from {data.timestamp}</span>
            </button>

            <div className="text-[10px] text-[#96546A] font-mono pt-1 flex justify-between border-t border-[#CDBEA9]/60">
              <span>Speaker: <strong className="text-[#4A1724]">{data.speaker}</strong> ({data.speakerTag})</span>
              <span>Voiceprint Confidence: <strong className="text-[#681F32]">{data.confidence}</strong></span>
            </div>
          </div>

          {/* Extraction Lineage */}
          <div className="p-4 rounded-xl bg-[#E9DFCE]/50 border border-[#CDBEA9] text-xs text-[#4A1724] font-mono space-y-1.5">
            <div className="text-[10px] text-[#96546A] uppercase font-bold">Extraction Lineage & Integrity</div>
            <div className="flex justify-between">
              <span>Speech Engine:</span>
              <span className="text-[#4A1724] font-bold">Whisper v3 (320kbps WAV)</span>
            </div>
            <div className="flex justify-between">
              <span>Extractor Pipeline:</span>
              <span className="text-[#4A1724] font-bold">{data.extractorVersion}</span>
            </div>
            <div className="flex justify-between">
              <span>Idempotent Sync:</span>
              <span className="text-[#681F32] font-bold">Jira / Linear v1 Sync Ready</span>
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-3 pt-2">
          {onConfirmAction && (
            <button
              onClick={() => {
                onConfirmAction();
                onClose();
              }}
              className="flex-1 py-2.5 rounded-xl bg-[#681F32] hover:bg-[#4A1724] text-[#FBF8F1] text-xs font-semibold shadow-lg flex items-center justify-center gap-2"
            >
              <Check className="w-4 h-4" />
              <span>Confirm AI Proposal</span>
            </button>
          )}
          <button
            onClick={onClose}
            className="px-4 py-2.5 rounded-xl bg-[#E9DFCE] hover:bg-[#CDBEA9] text-[#4A1724] text-xs font-semibold border border-[#CDBEA9]"
          >
            Close Inspector
          </button>
        </div>

      </div>
    </div>
  );
}
