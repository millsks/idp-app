/**
 * useAuth — the only way components should access authentication state.
 * Throws a clear error if called outside <AuthProvider>.
 */
import { useContext } from "react";
import { AuthContext, type AuthContextValue } from "../contexts/AuthContext";

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
