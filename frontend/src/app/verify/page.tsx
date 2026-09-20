"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { ShieldCheck, ShieldAlert, Clock, HelpCircle, CheckCircle2 } from "lucide-react";
import { apiClient } from "../../features/auth/auth-service";

type VerifyState = "LOADING" | "SUCCESS" | "EXPIRED" | "INVALID" | "ALREADY_VERIFIED";

function VerifyContent() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token");
  const [state, setState] = useState<VerifyState>("LOADING");
  const [errorMsg, setErrorMsg] = useState("");

  useEffect(() => {
    if (!token) {
      setState("INVALID");
      setErrorMsg("Verification token query parameter is missing.");
      return;
    }

    let active = true;

    const performVerification = async () => {
      try {
        await apiClient(`/auth/verify?token=${token}`, { method: "POST" });
        if (active) {
          setState("SUCCESS");
        }
      } catch (err) {
        if (active) {
          const msg = err instanceof Error ? err.message : "";
          setErrorMsg(msg);

          if (msg.toLowerCase().includes("expired")) {
            setState("EXPIRED");
          } else if (msg.toLowerCase().includes("already") || msg.toLowerCase().includes("consumed")) {
            setState("ALREADY_VERIFIED");
          } else {
            setState("INVALID");
          }
        }
      }
    };

    performVerification();

    return () => {
      active = false;
    };
  }, [token]);

  const renderContent = () => {
    switch (state) {
      case "LOADING":
        return (
          <>
            <div className="mx-auto h-12 w-12 border-4 border-olive-500 border-t-transparent rounded-full animate-spin" />
            <h2 className="text-2xl font-bold text-[#1a1a2e]">Activating Account</h2>
            <p className="text-sm text-[#6b6b8a]">Verifying signature claims and database memberships...</p>
          </>
        );
      case "SUCCESS":
        return (
          <>
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-600">
              <ShieldCheck className="h-6 w-6" />
            </div>
            <h2 className="text-2xl font-bold text-[#1a1a2e]">Identity Verified</h2>
            <p className="text-sm text-[#6b6b8a]">
              Your credentials are valid. We have initialized your default tenant workspace context.
            </p>
            <div className="pt-4">
              <Link
                href="/login"
                className="inline-block w-full rounded-lg bg-olive-600 hover:bg-olive-500 py-3 font-semibold text-white shadow-lg transition"
              >
                Sign In to Workspace
              </Link>
            </div>
          </>
        );
      case "EXPIRED":
        return (
          <>
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-yellow-500/10 border border-yellow-500/20 text-yellow-600">
              <Clock className="h-6 w-6" />
            </div>
            <h2 className="text-2xl font-bold text-[#1a1a2e]">Token Expired</h2>
            <p className="text-sm text-[#6b6b8a]">
              The 24-hour verification token lifetime has expired. Please re-register to obtain a new key.
            </p>
            <div className="pt-4">
              <Link
                href="/register"
                className="inline-block w-full rounded-lg bg-smoke hover:bg-seashell py-3 font-semibold text-[#3d3d5c] transition"
              >
                Go to Registration
              </Link>
            </div>
          </>
        );
      case "ALREADY_VERIFIED":
        return (
          <>
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-600">
              <CheckCircle2 className="h-6 w-6" />
            </div>
            <h2 className="text-2xl font-bold text-[#1a1a2e]">Already Verified</h2>
            <p className="text-sm text-[#6b6b8a]">
              This activation token has already been consumed. Your account workspace is fully operational.
            </p>
            <div className="pt-4">
              <Link
                href="/login"
                className="inline-block w-full rounded-lg bg-olive-600 hover:bg-olive-500 py-3 font-semibold text-white shadow-lg transition"
              >
                Sign In to Dashboard
              </Link>
            </div>
          </>
        );
      case "INVALID":
      default:
        return (
          <>
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-red-500/10 border border-red-500/20 text-red-600">
              <ShieldAlert className="h-6 w-6" />
            </div>
            <h2 className="text-2xl font-bold text-[#1a1a2e]">Invalid Verification Token</h2>
            <p className="text-sm text-[#6b6b8a]">
              {errorMsg || "The signature validation claims for this token are invalid or corrupted."}
            </p>
            <div className="pt-4">
              <Link
                href="/register"
                className="inline-block w-full rounded-lg bg-smoke hover:bg-seashell py-3 font-semibold text-[#3d3d5c] transition"
              >
                Re-request Registration
              </Link>
            </div>
          </>
        );
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-ghost via-snow to-white px-4">
      <div className="w-full max-w-md border border-[rgba(0,0,0,0.08)] bg-ivory/60 p-8 rounded-2xl text-center shadow-2xl backdrop-blur-xl space-y-6">
        {renderContent()}
      </div>
    </div>
  );
}

export default function VerifyPage() {
  return (
    <React.Suspense fallback={
      <div className="flex min-h-screen items-center justify-center bg-snow text-[#1a1a2e]">
        <div className="text-center space-y-4">
          <div className="mx-auto h-10 w-10 border-4 border-olive-500 border-t-transparent rounded-full animate-spin" />
          <p className="text-[#6b6b8a] text-sm">Loading verification details...</p>
        </div>
      </div>
    }>
      <VerifyContent />
    </React.Suspense>
  );
}
