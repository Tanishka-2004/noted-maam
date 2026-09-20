"use client";

import React, { createContext, useContext, useState, useEffect } from "react";

export type AppOperationalMode = "DEMO" | "REAL";

interface AppModeContextType {
  mode: AppOperationalMode;
  setMode: (mode: AppOperationalMode) => void;
  toggleMode: () => void;
}

const AppModeContext = createContext<AppModeContextType>({
  mode: "DEMO",
  setMode: () => {},
  toggleMode: () => {},
});

export function AppModeProvider({ children }: { children: React.ReactNode }) {
  const [mode, setModeState] = useState<AppOperationalMode>("DEMO");

  useEffect(() => {
    const saved = localStorage.getItem("noted_maam_mode");
    if (saved === "REAL" || saved === "DEMO") {
      setModeState(saved);
    }
  }, []);

  const setMode = (newMode: AppOperationalMode) => {
    setModeState(newMode);
    localStorage.setItem("noted_maam_mode", newMode);
  };

  const toggleMode = () => {
    const nextMode = mode === "DEMO" ? "REAL" : "DEMO";
    setMode(nextMode);
  };

  return (
    <AppModeContext.Provider value={{ mode, setMode, toggleMode }}>
      {children}
    </AppModeContext.Provider>
  );
}

export function useAppMode() {
  return useContext(AppModeContext);
}
