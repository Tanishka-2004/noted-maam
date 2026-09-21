"use client";

import React from "react";
import Link from "next/link";
import { Navigation } from "../../../components/Navigation";
import { TrustBadge } from "../../../components/TrustBadge";
import { useAppMode } from "../../../context/AppModeContext";
import { Activity, ArrowRight, FolderKanban, Plus } from "lucide-react";

export default function AppProjectsDirectoryPage() {
  const { mode } = useAppMode();

  const demoProjects = [
    { id: "proj_alpha", name: "Project Alpha", status: "Needs attention", statusBadge: "PARTIAL" as const, openBlockers: 3, overdueTasks: 2, desc: "Engineering Architecture & Auth Gateway Migration" },
    { id: "proj_nova", name: "Project Nova", status: "Healthy", statusBadge: "CONFIRMED" as const, openBlockers: 0, overdueTasks: 0, desc: "Client Onboarding & Telemetry Collector" },
    { id: "proj_website", name: "Website Redesign", status: "Healthy", statusBadge: "CONFIRMED" as const, openBlockers: 0, overdueTasks: 0, desc: "Marketing Homepage & Editorial Branding" },
  ];

  const projects = mode === "DEMO" ? demoProjects : [];

  return (
    <div className="min-h-screen bg-[#4A1724] text-[#FBF8F1] pb-16 font-sans">
      <Navigation />

      <main className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 pt-8 space-y-8">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[#681F32] pb-6">
          <div>
            <div className="flex items-center gap-2 text-xs font-semibold text-[#E9DFCE] mb-1">
              <Activity className="w-4 h-4 text-[#FBF8F1]" />
              <span>Project Directory & Intelligence Pulse</span>
            </div>
            <h1 className="text-3xl font-extrabold text-[#FBF8F1] tracking-tight font-display">Projects</h1>
            <p className="text-xs text-[#E9DFCE] font-medium mt-1">Track <strong>"What changed?"</strong> across active organizational projects.</p>
          </div>

          <Link
            href="/onboarding"
            className="px-4 py-2.5 rounded-xl bg-[#FBF8F1] hover:bg-[#F7F1E5] text-[#4A1724] font-bold text-xs flex items-center gap-2 transition-all shadow-md"
          >
            <Plus className="w-4 h-4 text-[#4A1724]" />
            <span>Create Real Project</span>
          </Link>
        </div>

        {mode === "REAL" && projects.length === 0 ? (
          <div className="p-12 rounded-2xl bg-[#5C1D2D] border border-[#7A2940] text-center space-y-4 shadow-md">
            <FolderKanban className="w-12 h-12 text-[#FBF8F1] mx-auto opacity-80" />
            <h3 className="text-lg font-bold text-[#FBF8F1]">No Real Projects Created Yet</h3>
            <p className="text-xs text-[#E9DFCE] max-w-md mx-auto">
              Your live workspace is connected. Create a project context or upload an unassigned meeting recording to organize team commitments.
            </p>
            <div className="pt-2">
              <Link
                href="/onboarding"
                className="px-5 py-2.5 rounded-xl bg-[#FBF8F1] hover:bg-[#F7F1E5] text-[#4A1724] font-bold text-xs inline-flex items-center gap-2 shadow-md"
              >
                <Plus className="w-4 h-4 text-[#4A1724]" />
                <span>Initialize First Project</span>
              </Link>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {projects.map((p) => (
              <div key={p.id} className="p-6 rounded-2xl bg-[#5C1D2D] border border-[#7A2940] flex flex-col justify-between space-y-4 hover:border-[#96546A] transition-all shadow-md">
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <TrustBadge state={p.statusBadge} customLabel={p.status} />
                    <span className="text-[10px] font-semibold text-[#E9DFCE]">ID: {p.id}</span>
                  </div>
                  <h3 className="font-bold text-lg text-[#FBF8F1]">{p.name}</h3>
                  <p className="text-xs text-[#E9DFCE] leading-relaxed font-medium">{p.desc}</p>
                </div>

                <div className="pt-3 border-t border-[#7A2940] flex items-center justify-between">
                  <span className="text-xs text-[#E9DFCE] font-medium">{p.openBlockers} Blockers · {p.overdueTasks} Overdue</span>
                  <Link
                    href={`/app/projects/${p.id}/pulse`}
                    className="px-3.5 py-1.5 rounded-lg bg-[#FBF8F1] text-[#4A1724] text-xs font-bold hover:bg-[#F7F1E5] transition-all flex items-center gap-1"
                  >
                    <span>PULSE →</span>
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
