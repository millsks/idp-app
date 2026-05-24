/**
 * API functions for authentication endpoints.
 */
import { apiClient } from "./client";

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface UserProfile {
  id: number;
  email: string;
  username: string;
  full_name: string | null;
  avatar_url: string | null;
  oauth_provider: string | null;
}

/** Exchange a one-time OAuth code for a JWT access token. */
export async function exchangeToken(exchangeCode: string): Promise<TokenResponse> {
  const response = await apiClient.post<TokenResponse>("/auth/token/exchange", {
    exchange_code: exchangeCode,
  });
  return response.data;
}

/**
 * Fetch the authenticated user's profile.
 * Implemented in Story 3.1 — may return null until then.
 */
export async function fetchCurrentUser(): Promise<UserProfile | null> {
  try {
    const response = await apiClient.get<UserProfile>("/users/me");
    return response.data;
  } catch {
    // Endpoint not yet live (Story 3.1) — return null gracefully.
    return null;
  }
}

/** Call the stateless logout endpoint (backend just returns 200). */
export async function callLogout(): Promise<void> {
  await apiClient.post("/auth/logout");
}
