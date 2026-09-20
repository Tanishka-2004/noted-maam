"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import zxcvbn from "zxcvbn";
import { Check, X, ShieldAlert, Eye, EyeOff } from "lucide-react";
import { apiClient } from "../../features/auth/auth-service";

export default function RegisterPage() {
  const router = useRouter();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  // Live zxcvbn strength state
  const [strengthScore, setStrengthScore] = useState<number>(0);
  const [strengthFeedback, setStrengthFeedback] = useState<string>("");
  const [suggestions, setSuggestions] = useState<string[]>([]);

  // Individual criteria checking states
  const meetsMinLength = password.length >= 10;
  const hasUppercase = /[A-Z]/.test(password);
  const hasLowercase = /[a-z]/.test(password);
  const hasNumber = /[0-9]/.test(password);
  const hasSymbol = /[^A-Za-z0-9]/.test(password);
  const passwordsMatch = password === confirmPassword && confirmPassword !== "";

  // Evaluate password strength live
  useEffect(() => {
    if (!password) {
      setStrengthScore(0);
      setStrengthFeedback("");
      setSuggestions([]);
      return;
    }

    const evaluation = zxcvbn(password);
    setStrengthScore(evaluation.score);
    setStrengthFeedback(evaluation.feedback.warning || "Good entropy profile.");
    setSuggestions(evaluation.feedback.suggestions || []);
  }, [password]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    // Clientside validations
    if (!meetsMinLength) {
      setError("Password fails length requirement.");
      return;
    }
    if (strengthScore < 3) {
      setError("Password strength score is too weak. Please include letters, numbers, and symbols.");
      return;
    }
    if (!passwordsMatch) {
      setError("Passwords do not match.");
      return;
    }

    setIsLoading(true);

    try {
      await apiClient("/auth/register", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      setSuccess(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed.");
    } finally {
      setIsLoading(false);
    }
  };

  const getStrengthColor = (score: number) => {
    switch (score) {
      case 0:
      case 1:
        return "bg-red-500";
      case 2:
        return "bg-orange-500";
      case 3:
        return "bg-yellow-500";
      case 4:
        return "bg-emerald-500";
      default:
        return "bg-[rgba(0,0,0,0.06)]";
    }
  };

  const getStrengthLabel = (score: number) => {
    switch (score) {
      case 0:
      case 1:
        return "Risky / Predictable";
      case 2:
        return "Moderate Entropy";
      case 3:
        return "Strong Password";
      case 4:
        return "Excellent Entropy";
      default:
        return "Empty";
    }
  };

  if (success) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-ghost via-snow to-white px-4">
        <div className="w-full max-w-md border border-[rgba(0,0,0,0.08)] bg-ivory/60 p-8 rounded-2xl text-center shadow-2xl backdrop-blur-xl space-y-6">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-600">
            <Check className="h-6 w-6" />
          </div>
          <h2 className="text-2xl font-bold text-[#1a1a2e]">Registration Successful!</h2>
          <p className="text-sm text-[#6b6b8a]">
            We have dispatched an activation email to <strong className="text-[#3d3d5c]">{email}</strong>.
            Please verify your link within 24 hours to access workspaces.
          </p>
          <div className="pt-2">
            <Link
              href="/login"
              className="inline-block rounded-lg bg-smoke hover:bg-seashell px-6 py-2.5 font-semibold text-[#3d3d5c] hover:text-[#1a1a2e] transition"
            >
              Return to Sign In
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-ghost via-snow to-white px-4 py-12 sm:px-6 lg:px-8">
      <div className="w-full max-w-md space-y-8">
        
        {/* Header */}
        <div className="text-center">
          <h2 className="text-4xl font-extrabold tracking-tight text-[#1a1a2e]">
            Get Started
          </h2>
          <p className="mt-2 text-sm text-[#6b6b8a]">
            Create your Noted Ma&apos;am account in seconds.
          </p>
        </div>

        {/* Card Form */}
        <div className="relative overflow-hidden rounded-2xl border border-[rgba(0,0,0,0.08)] bg-ivory/60 p-8 shadow-2xl backdrop-blur-xl">
          <div className="absolute inset-0 bg-gradient-to-tr from-olive-500/5 via-transparent to-emerald-500/5 pointer-events-none" />

          {error && (
            <div className="mb-4 rounded-lg bg-red-500/10 border border-red-500/20 p-3 text-xs text-red-600 flex gap-2">
              <ShieldAlert className="h-4 w-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Email Input */}
            <div>
              <label htmlFor="email" className="block text-xs font-semibold text-[#3d3d5c] uppercase tracking-wider">
                Email Address
              </label>
              <input
                id="email"
                type="email"
                required
                disabled={isLoading}
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="mt-1 block w-full rounded-lg border border-[rgba(0,0,0,0.1)] bg-smoke/60 px-4 py-2.5 text-[#1a1a2e] placeholder-[#6b6b8a] focus:border-olive-500 focus:outline-none focus:ring-1 focus:ring-olive-500 disabled:opacity-50 transition"
                placeholder="name@company.com"
              />
            </div>

            {/* Password Input */}
            <div>
              <label htmlFor="password" className="block text-xs font-semibold text-[#3d3d5c] uppercase tracking-wider">
                Create Password
              </label>
              <div className="relative mt-1">
                <input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  required
                  disabled={isLoading}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="block w-full rounded-lg border border-[rgba(0,0,0,0.1)] bg-smoke/60 px-4 py-2.5 text-[#1a1a2e] placeholder-[#6b6b8a] focus:border-olive-500 focus:outline-none pr-10 focus:ring-1 focus:ring-olive-500 disabled:opacity-50 transition"
                  placeholder="At least 10 characters"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-3 text-[#6b6b8a] hover:text-[#3d3d5c] transition"
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>

              {/* Entropy Bar and Warnings */}
              {password && (
                <div className="mt-3 space-y-2">
                  <div className="flex justify-between items-center text-[10px] font-semibold text-[#6b6b8a]">
                    <span>STRENGTH: {getStrengthLabel(strengthScore)}</span>
                    <span>SCORE: {strengthScore}/4</span>
                  </div>
                  
                  {/* Visual Strength Progress Segment */}
                  <div className="grid grid-cols-4 gap-1 h-1.5 rounded bg-smoke">
                    <div className={`h-full rounded-l transition-all duration-300 ${strengthScore >= 1 ? getStrengthColor(strengthScore) : "bg-transparent"}`} />
                    <div className={`h-full transition-all duration-300 ${strengthScore >= 2 ? getStrengthColor(strengthScore) : "bg-transparent"}`} />
                    <div className={`h-full transition-all duration-300 ${strengthScore >= 3 ? getStrengthColor(strengthScore) : "bg-transparent"}`} />
                    <div className={`h-full rounded-r transition-all duration-300 ${strengthScore >= 4 ? getStrengthColor(strengthScore) : "bg-transparent"}`} />
                  </div>

                  {strengthFeedback && (
                    <p className="text-[10px] text-[#6b6b8a] mt-1 italic leading-tight">
                      {strengthFeedback} {suggestions.length > 0 && suggestions[0]}
                    </p>
                  )}
                </div>
              )}
            </div>

            {/* Confirm Password Input */}
            <div>
              <label htmlFor="confirm-password" className="block text-xs font-semibold text-[#3d3d5c] uppercase tracking-wider">
                Confirm Password
              </label>
              <div className="relative mt-1">
                <input
                  id="confirm-password"
                  type={showConfirmPassword ? "text" : "password"}
                  required
                  disabled={isLoading}
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  className="block w-full rounded-lg border border-[rgba(0,0,0,0.1)] bg-smoke/60 px-4 py-2.5 text-[#1a1a2e] placeholder-[#6b6b8a] focus:border-olive-500 focus:outline-none pr-10 focus:ring-1 focus:ring-olive-500 disabled:opacity-50 transition"
                  placeholder="Re-enter password"
                />
                <button
                  type="button"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  className="absolute right-3 top-3 text-[#6b6b8a] hover:text-[#3d3d5c] transition"
                >
                  {showConfirmPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>

            {/* Checklist of Constraints */}
            <div className="p-4 bg-smoke/40 rounded-lg border border-[rgba(0,0,0,0.06)] grid grid-cols-2 gap-x-4 gap-y-2 text-[10px] font-semibold tracking-wider text-[#6b6b8a]">
              <div className={`flex items-center gap-1.5 ${meetsMinLength ? "text-emerald-600" : ""}`}>
                {meetsMinLength ? <Check className="h-3 w-3" /> : <X className="h-3 w-3 text-[rgba(0,0,0,0.2)]" />}
                <span>10+ CHARACTERS</span>
              </div>
              <div className={`flex items-center gap-1.5 ${hasUppercase ? "text-emerald-600" : ""}`}>
                {hasUppercase ? <Check className="h-3 w-3" /> : <X className="h-3 w-3 text-[rgba(0,0,0,0.2)]" />}
                <span>UPPERCASE LETTER</span>
              </div>
              <div className={`flex items-center gap-1.5 ${hasLowercase ? "text-emerald-600" : ""}`}>
                {hasLowercase ? <Check className="h-3 w-3" /> : <X className="h-3 w-3 text-[rgba(0,0,0,0.2)]" />}
                <span>LOWERCASE LETTER</span>
              </div>
              <div className={`flex items-center gap-1.5 ${hasNumber ? "text-emerald-600" : ""}`}>
                {hasNumber ? <Check className="h-3 w-3" /> : <X className="h-3 w-3 text-[rgba(0,0,0,0.2)]" />}
                <span>NUMERIC DIGIT</span>
              </div>
              <div className={`flex items-center gap-1.5 ${hasSymbol ? "text-emerald-600" : ""}`}>
                {hasSymbol ? <Check className="h-3 w-3" /> : <X className="h-3 w-3 text-[rgba(0,0,0,0.2)]" />}
                <span>SPECIAL SYMBOL</span>
              </div>
              <div className={`flex items-center gap-1.5 ${passwordsMatch ? "text-emerald-600" : ""}`}>
                {passwordsMatch ? <Check className="h-3 w-3" /> : <X className="h-3 w-3 text-[rgba(0,0,0,0.2)]" />}
                <span>PASSWORDS MATCH</span>
              </div>
            </div>

            {/* Register Action Button */}
            <button
              type="submit"
              disabled={isLoading || strengthScore < 3 || !passwordsMatch}
              className="w-full rounded-lg bg-olive-600 hover:bg-olive-500 py-3 font-semibold text-white shadow-lg shadow-olive-600/10 focus:outline-none focus:ring-2 focus:ring-olive-500 disabled:opacity-55 transition flex items-center justify-center"
            >
              {isLoading ? (
                <div className="h-5 w-5 animate-spin rounded-full border-2 border-white border-t-transparent" />
              ) : (
                "Create Account"
              )}
            </button>
          </form>

          {/* Login redirection */}
          <p className="mt-6 text-center text-sm text-[#6b6b8a]">
            Already have an account?{" "}
            <Link href="/login" className="font-medium text-olive-600 hover:underline hover:text-olive-500 transition">
              Sign In
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
