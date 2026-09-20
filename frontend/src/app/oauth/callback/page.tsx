"use client";

import React, { useEffect, useState } from "react";
import { useAuth } from "../../../features/auth/auth-provider";
import { useRouter } from "next/navigation";
import { ShieldCheck, ShieldAlert } from "lucide-react";

export default function OAuthCallbackPage() {
  const { refreshSession, status } = useAuth();
  const router = useRouter();
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    const performSync = async () => {
      try {
        // Trigger silent refresh to fetch the access token from the refresh cookie
        await refreshSession();
        if (active) {
          router.push("/sessions");
        }
      } catch (err) {
        if (active) {
          setErrorMsg("Failed to synchronize federated login session.");
          setTimeout(() => {
            router.push("/login?error=oauth_failed");
          }, 3000);
        }
      }
    };

    performSync();

    return () => {
      active = false;
    };
  }, []);

  return (
    <div className="flex min-h-screen items-center justify-center bg-snow text-[#1a1a2e] px-4">
      <div className="w-full max-w-md border border-[rgba(0,0,0,0.08)] bg-ivory/60 p-8 rounded-2xl text-center shadow-2xl backdrop-blur-xl space-y-6">
        {errorMsg ? (
          <>
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-red-500/10 border border-red-500/20 text-red-500">
              <ShieldAlert className="h-6 w-6" />
            </div>
            <h2 className="text-xl font-bold text-[#1a1a2e]">OAuth Sync Failed</h2>
            <p className="text-sm text-[#6b6b8a]">{errorMsg}</p>
            <p className="text-xs text-[#6b6b8a] animate-pulse">Redirecting back to login...</p>
          </>
        ) : (
          <>
            <div className="mx-auto h-12 w-12 border-4 border-olive-500 border-t-transparent rounded-full animate-spin" />
            <h2 className="text-xl font-bold text-[#1a1a2e]">Establishing Identity</h2>
            <p className="text-sm text-[#6b6b8a]">
              Restoring your workspace environment. Please wait.
            </p>
          </>
        )}
      </div>
    </div>
  );
}
