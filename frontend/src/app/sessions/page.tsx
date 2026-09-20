"use client";

import React, { useEffect, useState } from "react";
import { useAuth } from "../../features/auth/auth-provider";
import { useRouter } from "next/navigation";
import { Laptop, Globe, LogOut, CheckCircle2, Trash2, Smartphone, ShieldAlert } from "lucide-react";
import { apiClient } from "../../features/auth/auth-service";
import { UserSession } from "../../features/auth/auth-types";

export default function SessionsPage() {
  const { user, logout, status } = useAuth();
  const router = useRouter();

  const [sessions, setSessions] = useState<UserSession[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [revokingId, setRevokingId] = useState<string | null>(null);

  const fetchSessions = async () => {
    try {
      setError(null);
      const data = await apiClient<UserSession[]>("/auth/sessions");
      setSessions(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load active sessions");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    // Redirect if definitely unauthenticated (once state checks complete)
    if (status === "EXPIRED" || status === "LOGGED_OUT") {
      router.push("/login");
      return;
    }

    if (status === "AUTHENTICATED" || status === "REFRESHING") {
      fetchSessions();
    }
  }, [status]);

  const handleRevokeSession = async (sessionId: string) => {
    setRevokingId(sessionId);
    try {
      await apiClient(`/auth/sessions/${sessionId}`, {
        method: "DELETE",
      });
      // Immediately filter revoked session out of UI
      setSessions((prev) => prev.filter((s) => s.id !== sessionId));
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to revoke session");
    } finally {
      setRevokingId(null);
    }
  };

  // Mask IP Address for user privacy
  const maskIp = (ip?: string) => {
    if (!ip) return "Unknown IP";
    if (ip.includes(":")) {
      // IPv6 masking
      return ip.split(":").slice(0, 3).join(":") + "::/48";
    }
    // IPv4 masking
    const parts = ip.split(".");
    if (parts.length === 4) {
      return `${parts[0]}.${parts[1]}.***.***`;
    }
    return ip;
  };

  if (isLoading || status === "AUTHENTICATING" || status === "IDLE") {
    return (
      <div className="flex min-h-screen items-center justify-center bg-snow">
        <div className="text-center space-y-4">
          <div className="mx-auto h-10 w-10 border-4 border-olive-500 border-t-transparent rounded-full animate-spin" />
          <p className="text-[#6b6b8a] text-sm">Synchronizing dashboard workspace...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-snow text-[#1a1a2e]">
      
      {/* Navigation Header Bar */}
      <header className="border-b border-[rgba(0,0,0,0.06)] bg-ghost/60 backdrop-blur-md">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 flex h-16 items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-xl font-bold tracking-tight text-[#1a1a2e] font-mono">Noted Ma&apos;am</span>
            <span className="rounded bg-olive-500/10 border border-olive-500/20 px-2 py-0.5 text-[10px] font-semibold text-olive-600">
              Identity Portal
            </span>
          </div>

          <div className="flex items-center gap-4">
            <span className="text-xs text-[#6b6b8a]">{user?.email}</span>
            <button
              onClick={logout}
              className="flex items-center gap-1.5 rounded-lg border border-[rgba(0,0,0,0.1)] bg-smoke/40 hover:bg-red-500/10 hover:border-red-500/20 hover:text-red-600 px-3.5 py-1.5 text-xs font-semibold text-[#3d3d5c] transition"
            >
              <LogOut className="h-3.5 w-3.5" />
              <span>Sign Out</span>
            </button>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="mx-auto max-w-4xl px-4 py-12 sm:px-6 lg:px-8 space-y-8">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight text-[#1a1a2e]">Active Devices</h1>
          <p className="mt-1 text-sm text-[#6b6b8a]">
            Monitor and revoke active logins across different browser sessions.
          </p>
        </div>

        {error && (
          <div className="rounded-lg bg-red-500/10 border border-red-500/20 p-4 text-sm text-red-600 flex gap-2">
            <ShieldAlert className="h-5 w-5 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Sessions list */}
        <div className="divide-y divide-[rgba(0,0,0,0.06)] rounded-xl border border-[rgba(0,0,0,0.08)] bg-ivory/40 overflow-hidden shadow-xl">
          {sessions.length === 0 ? (
            <div className="p-8 text-center text-[#6b6b8a] text-sm">
              No active sessions identified.
            </div>
          ) : (
            sessions.map((session, index) => {
              const isCurrent = index === 0; // The first session returned (sorted desc) is the active tab
              const device = session.device;

              return (
                <div key={session.id} className="p-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 hover:bg-seashell/40 transition">
                  <div className="flex gap-4 items-start">
                    {/* Device Icon */}
                    <div className="p-3 rounded-lg border border-[rgba(0,0,0,0.08)] bg-smoke/40 text-[#6b6b8a] shrink-0">
                      {device?.operating_system?.toLowerCase().includes("ios") || 
                       device?.operating_system?.toLowerCase().includes("android") ? (
                        <Smartphone className="h-6 w-6" />
                      ) : (
                        <Laptop className="h-6 w-6" />
                      )}
                    </div>

                    {/* Metadata detail block */}
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-[#1a1a2e]">
                          {device?.browser || "Unknown Browser"} on {device?.operating_system || "Unknown OS"}
                        </span>
                        {isCurrent && (
                          <span className="flex items-center gap-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 text-[10px] font-semibold text-emerald-600">
                            <CheckCircle2 className="h-3 w-3" />
                            Current Device
                          </span>
                        )}
                      </div>

                      <div className="text-xs text-[#6b6b8a] flex flex-wrap items-center gap-x-3 gap-y-1">
                        <span className="flex items-center gap-1">
                          <Globe className="h-3.5 w-3.5 text-[#6b6b8a]" />
                          <span>IP: {maskIp(device?.ip_address)}</span>
                        </span>
                        <span>•</span>
                        <span>Location: {device?.geographic_location || "Unknown Location"}</span>
                      </div>

                      <div className="text-[10px] text-[#6b6b8a] font-semibold uppercase tracking-wider">
                        Created: {new Date(session.created_at).toLocaleString()}
                      </div>
                    </div>
                  </div>

                  {/* Revoke control button */}
                  <div>
                    {!isCurrent && (
                      <button
                        onClick={() => handleRevokeSession(session.id)}
                        disabled={revokingId === session.id}
                        className="w-full sm:w-auto flex items-center justify-center gap-1.5 rounded-lg border border-[rgba(0,0,0,0.1)] bg-smoke/20 hover:bg-red-500/10 hover:border-red-500/20 hover:text-red-600 px-4 py-2 text-xs font-semibold text-[#6b6b8a] transition"
                      >
                        {revokingId === session.id ? (
                          <div className="h-3.5 w-3.5 animate-spin rounded-full border border-[#6b6b8a] border-t-transparent" />
                        ) : (
                          <>
                            <Trash2 className="h-3.5 w-3.5" />
                            <span>Revoke Session</span>
                          </>
                        )}
                      </button>
                    )}
                  </div>
                </div>
              );
            })
          )}
        </div>
      </main>
    </div>
  );
}
