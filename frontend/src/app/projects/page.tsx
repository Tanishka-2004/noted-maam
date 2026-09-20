"use client";

import React from "react";
import Link from "next/link";
import { Navigation } from "../../components/Navigation";
import { TrustBadge } from "../../components/TrustBadge";
import { DemoModeBanner } from "../../components/DemoModeBanner";
import { Activity, ArrowRight, FolderKanban } from "lucide-react";

export default function ProjectsDirectoryPage() {
  const projects = [
    { id: "proj_alpha", name: "Project Alpha", status: "Needs attention", statusBadge: "PARTIAL" as const, openBlockers: 3, overdueTasks: 2, desc: "Engineering Architecture & Auth Gateway Migration" },
    { id: "proj_nova", name: "Project Nova", status: "Healthy", statusBadge: "CONFIRMED" as const, openBlockers: 0, overdueTasks: 0, desc: "Client Onboarding & Telemetry Collector" },
    { id: "proj_website", name: "Website Redesign", status: "Healthy", statusBadge: "CONFIRMED" as const, openBlockers: 0, overdueTasks: 0, desc: "Marketing Homepage & Editorial Branding" },
  ];

  return (
    <div className="min-h-screen bg-[#FBF8F1] text-[#4A1724] pb-16">
      <DemoModeBanner />
      <Navigation />

      <main className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 pt-8 space-y-8">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[#CDBEA9] pb-6">
          <div>
            <div className="flex items-center gap-2 text-xs font-mono text-[#681F32] font-bold mb-1">
              <Activity className="w-4 h-4 text-[#681F32]" />
              <span>Project Directory & Intelligence Pulse</span>
            </div>
            <h1 className="text-3xl font-extrabold text-[#4A1724] tracking-tight">Projects</h1>
            <p className="text-xs text-[#96546A] font-medium mt-1">Track <strong>"What changed?"</strong> across active organizational projects.</p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {projects.map((p) => (
            <div key={p.id} className="p-6 rounded-2xl bg-[#F7F1E5] border border-[#CDBEA9] flex flex-col justify-between space-y-4 hover:border-[#7A2940] transition-all">
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <TrustBadge state={p.statusBadge} customLabel={p.status} />
                  <span className="text-[10px] font-mono text-[#96546A] font-bold">ID: {p.id}</span>
                </div>
                <h3 className="font-bold text-lg text-[#4A1724]">{p.name}</h3>
                <p className="text-xs text-[#4A1724] leading-relaxed">{p.desc}</p>
              </div>

              <div className="pt-3 border-t border-[#CDBEA9] flex items-center justify-between">
                <span className="text-xs text-[#96546A] font-mono">{p.openBlockers} Blockers · {p.overdueTasks} Overdue</span>
                <Link
                  href={`/projects/${p.id}/pulse`}
                  className="px-3.5 py-1.5 rounded-lg bg-[#681F32] text-[#FBF8F1] text-xs font-semibold hover:bg-[#4A1724] transition-all flex items-center gap-1 font-mono"
                >
                  <span>PULSE →</span>
                </Link>
              </div>
            </div>
          ))}
        </div>
      </main>
    </div>
  );
}
