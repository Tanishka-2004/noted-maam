import React from "react";
import type { Metadata } from "next";
import "../styles/globals.css";
import { AuthProvider } from "../features/auth/auth-provider";
import { AppModeProvider } from "../context/AppModeContext";
import { LiveMeetingProvider } from "../context/LiveMeetingContext";
import { LiveMeetingBar } from "../components/LiveMeetingBar";
import { LiveMeetingModal } from "../components/LiveMeetingModal";

export const metadata: Metadata = {
  title: "Noted Ma'am — Meeting Operating System",
  description: "Turn conversations into verified decisions, accountable commitments, and searchable project memory.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased bg-[#4A1724] text-[#FBF8F1] selection:bg-[#681F32] selection:text-[#FBF8F1]">
        <AuthProvider>
          <AppModeProvider>
            <LiveMeetingProvider>
              {children}
              <LiveMeetingBar />
              <LiveMeetingModal />
            </LiveMeetingProvider>
          </AppModeProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
