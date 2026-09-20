import { TokenResponse, User, UserSession } from "./auth-types";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

let memoryToken: string | null = null;
let refreshPromise: Promise<string> | null = null;

// Initialize BroadcastChannel for multi-tab state sync
const authChannel = typeof window !== "undefined" ? new BroadcastChannel("auth_channel") : null;

export function setMemoryToken(token: string | null) {
  memoryToken = token;
  if (token && authChannel) {
    authChannel.postMessage({ type: "LOGIN" });
  }
}

export function getMemoryToken() {
  return memoryToken;
}

export function broadcastLogout() {
  memoryToken = null;
  authChannel?.postMessage({ type: "LOGOUT" });
}

export function listenToAuthChannel(callback: (event: { type: string }) => void) {
  if (!authChannel) return () => {};
  const handler = (e: MessageEvent) => callback(e.data);
  authChannel.addEventListener("message", handler);
  return () => {
    authChannel.removeEventListener("message", handler);
  };
}

/**
 * Executes token refresh. Utilizes credentials: 'include' to pass refresh_token cookie.
 */
async function executeRefresh(): Promise<string> {
  try {
    const res = await fetch(`${BASE_URL}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
    });

    if (!res.ok) {
      throw new Error("Token rotation failed");
    }

    const data: TokenResponse = await res.json();
    setMemoryToken(data.access_token);
    return data.access_token;
  } catch (error) {
    setMemoryToken(null);
    broadcastLogout();
    throw error;
  }
}

/**
 * Shared promise / mutex to prevent duplicate simultaneous refresh requests.
 */
export async function getOrRotateToken(): Promise<string> {
  if (refreshPromise) {
    return refreshPromise;
  }

  refreshPromise = executeRefresh().finally(() => {
    refreshPromise = null;
  });

  return refreshPromise;
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

/**
 * Centralized API client wrapper with auto-auth injection, request queuing, and retries.
 */
export async function apiClient<T>(path: string, options: RequestInit = {}): Promise<T> {
  const url = `${BASE_URL}${path}`;
  const headers = new Headers(options.headers || {});

  // 1. Inject memory token if present
  if (memoryToken) {
    headers.set("Authorization", `Bearer ${memoryToken}`);
  }

  // 2. Set default content type
  if (!headers.has("Content-Type") && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  const mergedOptions: RequestInit = {
    ...options,
    headers,
    credentials: "include", // Ensure cookies are sent
  };

  try {
    let res = await fetch(url, mergedOptions);

    // 3. Intercept 401 Unauthorized errors (excluding auth registration and verification)
    const isAuthRoute = path.includes("/auth/login") || path.includes("/auth/register") || path.includes("/auth/refresh");
    
    if (res.status === 401 && !isAuthRoute) {
      try {
        // Attempt token rotation
        const newToken = await getOrRotateToken();
        
        // Re-inject new token and retry request
        headers.set("Authorization", `Bearer ${newToken}`);
        res = await fetch(url, { ...mergedOptions, headers });
      } catch (refreshErr) {
        throw new ApiError(401, "Session expired. Please log in again.");
      }
    }

    if (!res.ok) {
      let errMsg = "An error occurred";
      try {
        const errorJson = await res.json();
        errMsg = errorJson.detail || errMsg;
      } catch {}
      throw new ApiError(res.status, errMsg);
    }

    if (res.status === 204) {
      return {} as T;
    }

    return await res.json() as T;
  } catch (err) {
    if (err instanceof ApiError) {
      throw err;
    }
    throw new Error(err instanceof Error ? err.message : "Network request failed");
  }
}
