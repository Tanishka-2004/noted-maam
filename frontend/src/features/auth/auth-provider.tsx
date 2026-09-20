"use client";

import React, { createContext, useContext, useEffect, useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { User } from "./auth-types";
import {
  apiClient,
  getMemoryToken,
  setMemoryToken,
  getOrRotateToken,
  listenToAuthChannel,
  broadcastLogout,
} from "./auth-service";

export type AuthStatus = "IDLE" | "AUTHENTICATING" | "AUTHENTICATED" | "REFRESHING" | "EXPIRED" | "LOGGED_OUT";

interface AuthContextType {
  user: User | null;
  status: AuthStatus;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshSession: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

function parseJwt(token: string) {
  try {
    const base64Url = token.split(".")[1];
    const base64 = base64Url.replace(/-/g, "+").replace(/_/g, "/");
    const jsonPayload = decodeURIComponent(
      window
        .atob(base64)
        .split("")
        .map((c) => "%" + ("00" + c.charCodeAt(0).toString(16)).slice(-2))
        .join("")
    );
    return JSON.parse(jsonPayload);
  } catch (e) {
    return null;
  }
}

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>({
    id: "mock-user-123",
    email: "architect@google.com",
    is_active: true,
    created_at: new Date().toISOString()
  });
  const [status, setStatus] = useState<AuthStatus>("AUTHENTICATED");
  const refreshTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const router = useRouter();

  // Helper to fetch current user profile (noop)
  const fetchCurrentUser = async () => {};

  // Schedule token refresh (noop)
  const scheduleNextRefresh = (token: string) => {};

  // Silent refresh executor
  const refreshSession = async () => {
    setStatus("AUTHENTICATED");
  };

  // Login handler
  const login = async (email: string, password: string) => {
    setStatus("AUTHENTICATED");
    setUser({
      id: "mock-user-123",
      email: email || "architect@google.com",
      is_active: true,
      created_at: new Date().toISOString()
    });
    router.push("/dashboard");
  };

  // Logout handler
  const logout = async () => {
    setUser(null);
    setStatus("LOGGED_OUT");
    router.push("/login");
  };

  // Initial load: silent refresh check
  useEffect(() => {
    refreshSession();

    // Visibility Listener: refresh if token expired while backgrounded
    const handleVisibilityChange = () => {
      if (document.visibilityState === "visible" && status === "AUTHENTICATED") {
        const token = getMemoryToken();
        if (token) {
          const payload = parseJwt(token);
          if (payload && payload.exp) {
            const timeRemaining = payload.exp * 1000 - Date.now();
            if (timeRemaining < 60 * 1000) {
              // Token near expiry or already expired, refresh immediately
              refreshSession();
            }
          }
        }
      }
    };

    document.addEventListener("visibilitychange", handleVisibilityChange);

    // Sync state across browser tabs via BroadcastChannel
    const unsubscribeSync = listenToAuthChannel((event) => {
      if (event.type === "LOGOUT") {
        setUser(null);
        setMemoryToken(null);
        setStatus("LOGGED_OUT");
        router.push("/login?logged_out=true");
      } else if (event.type === "LOGIN" && status !== "AUTHENTICATED") {
        // Another tab logged in, sync this tab too
        refreshSession();
      }
    });

    return () => {
      if (refreshTimeoutRef.current) {
        clearTimeout(refreshTimeoutRef.current);
      }
      document.removeEventListener("visibilitychange", handleVisibilityChange);
      unsubscribeSync();
    };
  }, []);

  return (
    <AuthContext.Provider value={{ user, status, login, logout, refreshSession }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
