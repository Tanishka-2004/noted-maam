"use client";

import React, { useState, useEffect } from "react";
import { useAuth } from "../../features/auth/auth-provider";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Eye, EyeOff, ShieldAlert, Chrome } from "lucide-react";

function LoginForm() {
  const { login, status } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [capsLock, setCapsLock] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const isExpired = searchParams.get("expired") === "true";
  const isLoggedOut = searchParams.get("logged_out") === "true";

  // Check for Caps Lock key activation
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.getModifierState("CapsLock")) {
      setCapsLock(true);
    } else {
      setCapsLock(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    try {
      await login(email, password);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Authentication failed");
    } finally {
      setIsLoading(false);
    }
  };

  const handleGoogleLogin = () => {
    // Redirect browser directly to backend Google OAuth initiation gateway
    window.location.href = "http://localhost:8000/api/v1/auth/oauth/google";
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-ghost via-snow to-white px-4 py-12 sm:px-6 lg:px-8">
      <div className="w-full max-w-md space-y-8">
        
        {/* Branding header */}
        <div className="text-center">
          <h2 className="text-4xl font-extrabold tracking-tight text-[#1a1a2e] sm:text-5xl">
            Noted Ma&apos;am
          </h2>
          <p className="mt-3 text-sm text-[#6b6b8a]">
            Sign in to access your meeting intelligence environment.
          </p>
        </div>

        {/* Form Container */}
        <div className="relative overflow-hidden rounded-2xl border border-[rgba(0,0,0,0.08)] bg-ivory/60 p-8 shadow-2xl backdrop-blur-xl">
          <div className="absolute inset-0 bg-gradient-to-tr from-olive-500/5 via-transparent to-emerald-500/5 pointer-events-none" />

          {/* Expiry / Signout Notification Alerts */}
          {isExpired && (
            <div className="mb-4 rounded-lg bg-yellow-500/10 border border-yellow-500/20 p-3 text-xs text-yellow-700 flex items-center gap-2">
              <ShieldAlert className="h-4 w-4" />
              <span>Your session has expired. Please log in again.</span>
            </div>
          )}

          {isLoggedOut && (
            <div className="mb-4 rounded-lg bg-emerald-500/10 border border-emerald-500/20 p-3 text-xs text-emerald-700 flex items-center gap-2">
              <span>You have been successfully logged out from all tabs.</span>
            </div>
          )}

          {error && (
            <div className="mb-4 rounded-lg bg-red-500/10 border border-red-500/20 p-3 text-xs text-red-600">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-6" onKeyDown={handleKeyDown}>
            {/* Email Input */}
            <div>
              <label htmlFor="email" className="block text-xs font-semibold text-[#3d3d5c] uppercase tracking-wider">
                Email Address
              </label>
              <input
                id="email"
                name="email"
                type="email"
                required
                disabled={isLoading || status === "AUTHENTICATING"}
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="mt-1 block w-full rounded-lg border border-[rgba(0,0,0,0.1)] bg-smoke/60 px-4 py-3 text-[#1a1a2e] placeholder-[#6b6b8a] focus:border-olive-500 focus:outline-none focus:ring-1 focus:ring-olive-500 disabled:opacity-50 transition"
                placeholder="you@example.com"
              />
            </div>

            {/* Password Input */}
            <div>
              <div className="flex justify-between items-center">
                <label htmlFor="password" className="block text-xs font-semibold text-[#3d3d5c] uppercase tracking-wider">
                  Password
                </label>
                <Link href="/forgot-password" className="text-xs text-[#6b6b8a] hover:text-olive-600 transition">
                  Forgot?
                </Link>
              </div>
              <div className="relative mt-1">
                <input
                  id="password"
                  name="password"
                  type={showPassword ? "text" : "password"}
                  required
                  disabled={isLoading || status === "AUTHENTICATING"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="block w-full rounded-lg border border-[rgba(0,0,0,0.1)] bg-smoke/60 px-4 py-3 text-[#1a1a2e] placeholder-[#6b6b8a] focus:border-olive-500 focus:outline-none focus:ring-1 focus:ring-olive-500 disabled:opacity-50 pr-10 transition"
                  placeholder="••••••••••••"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-3.5 text-[#6b6b8a] hover:text-[#3d3d5c] transition"
                >
                  {showPassword ? <EyeOff className="h-4.5 w-4.5" /> : <Eye className="h-4.5 w-4.5" />}
                </button>
              </div>

              {/* Caps Lock warning indicator */}
              {capsLock && (
                <div className="mt-2 text-xs text-yellow-600 flex items-center gap-1.5 animate-pulse">
                  <ShieldAlert className="h-3.5 w-3.5" />
                  <span>Caps Lock is ON</span>
                </div>
              )}
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={isLoading || status === "AUTHENTICATING"}
              className="relative w-full rounded-lg bg-olive-600 py-3 font-semibold text-white shadow-lg shadow-olive-600/20 hover:bg-olive-500 focus:outline-none focus:ring-2 focus:ring-olive-500 focus:ring-offset-2 focus:ring-offset-snow transition-all disabled:opacity-55 flex items-center justify-center gap-2"
            >
              {isLoading || status === "AUTHENTICATING" ? (
                <div className="h-5 w-5 animate-spin rounded-full border-2 border-white border-t-transparent" />
              ) : (
                "Continue"
              )}
            </button>
          </form>

          {/* Social Divider */}
          <div className="relative my-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-[rgba(0,0,0,0.08)]" />
            </div>
            <div className="relative flex justify-center text-xs uppercase">
              <span className="bg-ivory/60 px-2 text-[#6b6b8a]">Or continue with</span>
            </div>
          </div>

          {/* Google SSO button */}
          <button
            type="button"
            onClick={handleGoogleLogin}
            disabled={isLoading || status === "AUTHENTICATING"}
            className="w-full flex items-center justify-center gap-3 rounded-lg border border-[rgba(0,0,0,0.1)] bg-smoke/40 hover:bg-smoke/80 py-3 font-semibold text-[#3d3d5c] hover:text-[#1a1a2e] transition disabled:opacity-55"
          >
            <Chrome className="h-5 w-5 text-[#6b6b8a] group-hover:text-[#1a1a2e]" />
            <span>Google Workplace Single Sign-On</span>
          </button>

          {/* Register Redirect link */}
          <p className="mt-6 text-center text-sm text-[#6b6b8a]">
            Don&apos;t have an account?{" "}
            <Link href="/register" className="font-medium text-olive-600 hover:underline hover:text-olive-500 transition">
              Create an account
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <React.Suspense fallback={
      <div className="flex min-h-screen items-center justify-center bg-snow text-[#1a1a2e]">
        <div className="text-center space-y-4">
          <div className="mx-auto h-10 w-10 border-4 border-olive-500 border-t-transparent rounded-full animate-spin" />
          <p className="text-[#6b6b8a] text-sm">Syncing session state...</p>
        </div>
      </div>
    }>
      <LoginForm />
    </React.Suspense>
  );
}
