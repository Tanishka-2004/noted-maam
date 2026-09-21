"use client";

import React, { createContext, useContext, useState, useEffect, useRef } from "react";

export interface LiveTranscriptItem {
  id: string;
  speaker: string;
  speakerTag: string;
  timestamp: string;
  text: string;
}

export interface LiveExtractedItem {
  id: string;
  type: "ACTION" | "DECISION" | "CONFLICT";
  title: string;
  assignee?: string;
  evidence: string;
  confidence: string;
  trustBadge: "CONFIRMED" | "PARTIAL" | "CONFLICTING";
}

interface LiveMeetingContextType {
  isRecording: boolean;
  isPaused: boolean;
  isModalOpen: boolean;
  elapsedSeconds: number;
  meetingTitle: string;
  selectedProject: string;
  audioSourceMode: "MIC_ONLY" | "SYSTEM_TAB_AUDIO";
  transcript: LiveTranscriptItem[];
  extractedItems: LiveExtractedItem[];
  startMeeting: (title?: string, project?: string, sourceMode?: "MIC_ONLY" | "SYSTEM_TAB_AUDIO") => void;
  pauseMeeting: () => void;
  resumeMeeting: () => void;
  endMeeting: () => void;
  openModal: () => void;
  closeModal: () => void;
  setAudioSourceMode: (mode: "MIC_ONLY" | "SYSTEM_TAB_AUDIO") => void;
  setSelectedProject: (proj: string) => void;
  setMeetingTitle: (title: string) => void;
}

const LiveMeetingContext = createContext<LiveMeetingContextType | undefined>(undefined);

const DEMO_SPEECH_STREAM: { speaker: string; speakerTag: string; text: string; actionExtract?: LiveExtractedItem }[] = [
  { 
    speaker: "Tanishka", 
    speakerTag: "SPEAKER_01", 
    text: "Alright team, let's start the Q3 Auth Gateway and Infrastructure sync. We need to align on deliverables." 
  },
  { 
    speaker: "Rahul Sharma", 
    speakerTag: "SPEAKER_02", 
    text: "Target launch date for the auth gateway is currently set to October 12th, but QA requires 4 more days.",
  },
  { 
    speaker: "Rahul Sharma", 
    speakerTag: "SPEAKER_02", 
    text: "I propose we officially supersede the target launch date from October 12th to October 19th.",
    actionExtract: {
      id: "live_dec_1",
      type: "DECISION",
      title: "Target launch date superseded from Oct 12 to Oct 19",
      assignee: "Rahul Sharma",
      evidence: "Verbal proposal by Rahul Sharma during live sync",
      confidence: "99%",
      trustBadge: "CONFIRMED"
    }
  },
  { 
    speaker: "Rohan Varma", 
    speakerTag: "SPEAKER_03", 
    text: "I will finalize the OpenAPI contract endpoints for v2.1 auth gateway by Friday afternoon 17:00 UTC.",
    actionExtract: {
      id: "live_act_1",
      type: "ACTION",
      title: "Finalize OpenAPI contract endpoints for v2.1 auth gateway",
      assignee: "Rohan Varma",
      evidence: "Explicit verbal commitment by Rohan Varma",
      confidence: "98%",
      trustBadge: "CONFIRMED"
    }
  },
  { 
    speaker: "Sarah Jenkins", 
    speakerTag: "SPEAKER_04", 
    text: "Wait, the security compliance telemetry audit is scheduled for Oct 15. Disagreement between launch target and audit window!",
    actionExtract: {
      id: "live_cnf_1",
      type: "CONFLICT",
      title: "Position Disagreement: Telemetry Audit Window vs Oct 19 Launch Target",
      assignee: "Sarah Jenkins",
      evidence: "Divergence detected between compliance requirement and target release date",
      confidence: "94%",
      trustBadge: "CONFLICTING"
    }
  },
  { 
    speaker: "Aarohi Sharma", 
    speakerTag: "SPEAKER_05", 
    text: "I can run the Alembic database migration verification scripts on test_iam DB by tomorrow morning.",
    actionExtract: {
      id: "live_act_2",
      type: "ACTION",
      title: "Verify database migration scripts on test_iam DB",
      assignee: "Aarohi Sharma",
      evidence: "Proposed action item during live ingestion",
      confidence: "96%",
      trustBadge: "CONFIRMED"
    }
  }
];

export function LiveMeetingProvider({ children }: { children: React.ReactNode }) {
  const [isRecording, setIsRecording] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [meetingTitle, setMeetingTitle] = useState("Live Sync — Q3 Product & Auth Architecture");
  const [selectedProject, setSelectedProject] = useState("Project Alpha");
  const [audioSourceMode, setAudioSourceMode] = useState<"MIC_ONLY" | "SYSTEM_TAB_AUDIO">("SYSTEM_TAB_AUDIO");
  const [transcript, setTranscript] = useState<LiveTranscriptItem[]>([]);
  const [extractedItems, setExtractedItems] = useState<LiveExtractedItem[]>([]);

  const streamIndexRef = useRef(0);
  const mediaStreamRef = useRef<MediaStream | null>(null);

  // Timer effect
  useEffect(() => {
    let interval: NodeJS.Timeout | null = null;
    if (isRecording && !isPaused) {
      interval = setInterval(() => {
        setElapsedSeconds((prev) => prev + 1);
      }, 1000);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isRecording, isPaused]);

  // Simulated Speech and Real-time AI extraction effect
  useEffect(() => {
    let speechInterval: NodeJS.Timeout | null = null;
    if (isRecording && !isPaused) {
      speechInterval = setInterval(() => {
        const nextItem = DEMO_SPEECH_STREAM[streamIndexRef.current % DEMO_SPEECH_STREAM.length];
        streamIndexRef.current += 1;

        const minutes = Math.floor(elapsedSeconds / 60).toString().padStart(2, "0");
        const seconds = (elapsedSeconds % 60).toString().padStart(2, "0");
        const timeStr = `${minutes}:${seconds}`;

        const newTranscriptItem: LiveTranscriptItem = {
          id: `t_${Date.now()}_${streamIndexRef.current}`,
          speaker: nextItem.speaker,
          speakerTag: nextItem.speakerTag,
          timestamp: timeStr,
          text: nextItem.text,
        };

        setTranscript((prev) => [...prev, newTranscriptItem]);

        if (nextItem.actionExtract) {
          setExtractedItems((prev) => {
            if (prev.some(item => item.id === nextItem.actionExtract?.id)) return prev;
            return [nextItem.actionExtract!, ...prev];
          });
        }
      }, 3500);
    }
    return () => {
      if (speechInterval) clearInterval(speechInterval);
    };
  }, [isRecording, isPaused, elapsedSeconds]);

  const startMeeting = async (title?: string, project?: string, sourceMode?: "MIC_ONLY" | "SYSTEM_TAB_AUDIO") => {
    if (title) setMeetingTitle(title);
    if (project) setSelectedProject(project);
    const chosenMode = sourceMode || audioSourceMode;

    try {
      if (chosenMode === "SYSTEM_TAB_AUDIO" && navigator.mediaDevices && navigator.mediaDevices.getDisplayMedia) {
        // System / Tab Audio capture (captures speaker audio directly when wearing headphones!)
        const displayStream = await navigator.mediaDevices.getDisplayMedia({
          audio: true,
          video: true
        });
        mediaStreamRef.current = displayStream;
      } else if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        // Mic-only fallback
        const micStream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaStreamRef.current = micStream;
      }
    } catch (e) {
      console.warn("Audio stream permission prompt bypassed or canceled:", e);
    }

    setIsRecording(true);
    setIsPaused(false);
    setIsModalOpen(true);
  };

  const pauseMeeting = () => {
    setIsPaused(true);
  };

  const resumeMeeting = () => {
    setIsPaused(false);
  };

  const endMeeting = () => {
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((track) => track.stop());
      mediaStreamRef.current = null;
    }
    setIsRecording(false);
    setIsPaused(false);
    setIsModalOpen(false);
  };

  const openModal = () => setIsModalOpen(true);
  const closeModal = () => setIsModalOpen(false);

  return (
    <LiveMeetingContext.Provider
      value={{
        isRecording,
        isPaused,
        isModalOpen,
        elapsedSeconds,
        meetingTitle,
        selectedProject,
        audioSourceMode,
        transcript,
        extractedItems,
        startMeeting,
        pauseMeeting,
        resumeMeeting,
        endMeeting,
        openModal,
        closeModal,
        setAudioSourceMode,
        setSelectedProject,
        setMeetingTitle,
      }}
    >
      {children}
    </LiveMeetingContext.Provider>
  );
}

export function useLiveMeeting() {
  const ctx = useContext(LiveMeetingContext);
  if (!ctx) throw new Error("useLiveMeeting must be used within a LiveMeetingProvider");
  return ctx;
}
