/**
 * AuthContext — in-memory authentication state for the app.
 *
 * Design decisions (from Architecture §2.4):
 * - JWT stored in `useRef<string | null>`, never in React state or browser storage.
 *   Survives re-renders; lost on page close / refresh (intentional per PRD FR-2.7).
 * - `getAuthToken()` is exported from `tokenStore.ts` so the Axios interceptor can
 *   read the token without importing this context (avoids circular imports).
 */
import { createContext, useCallback, useEffect, useRef, useState, type ReactNode } from "react";

import { callLogout, exchangeToken, fetchCurrentUser, type UserProfile } from "../api/auth";
import { setAuthToken, setLogoutCallback } from "../utils/tokenStore";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface AuthContextValue {
  user: UserProfile | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (exchangeCode: string) => Promise<void>;
  logout: () => void;
}

// ---------------------------------------------------------------------------
// Context
// ---------------------------------------------------------------------------

const AuthContext = createContext<AuthContextValue | null>(null);

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------

export function AuthProvider({ children }: { children: ReactNode }) {
  const tokenRef = useRef<string | null>(null);
  const [user, setUser] = useState<UserProfile | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const logout = useCallback(() => {
    tokenRef.current = null;
    setAuthToken(null);
    setUser(null);
    setIsAuthenticated(false);
    // Best-effort — ignore errors (token may already be expired).
    callLogout().catch(() => {
      /* ignore */
    });
  }, []);

  // Register the logout fn so the Axios 401 interceptor can trigger it.
  useEffect(() => {
    setLogoutCallback(logout);
    return () => {
      setLogoutCallback(() => {
        /* unregistered */
      });
    };
  }, [logout]);

  const login = useCallback(async (exchangeCode: string) => {
    setIsLoading(true);
    try {
      const { access_token } = await exchangeToken(exchangeCode);
      tokenRef.current = access_token;
      setAuthToken(access_token);
      setIsAuthenticated(true);
      // Story 3.1: /users/me — fetchCurrentUser returns null if not yet live.
      const profile = await fetchCurrentUser();
      setUser(profile);
    } finally {
      setIsLoading(false);
    }
  }, []);

  return (
    <AuthContext.Provider value={{ user, isAuthenticated, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

// ---------------------------------------------------------------------------
// Internal context export (consumed by useAuth hook in hooks/useAuth.ts)
// ---------------------------------------------------------------------------

export { AuthContext };
export type { AuthContextValue };
