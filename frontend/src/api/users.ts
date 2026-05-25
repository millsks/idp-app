/**
 * API functions for /users/me endpoints.
 */
import { apiClient } from "./client";

export interface UserMe {
  id: number;
  email: string;
  full_name: string | null;
  avatar_url: string | null;
  oauth_provider: string | null;
  is_active: boolean;
  is_superuser: boolean;
  created_at: string;
}

export interface UserMeUpdate {
  full_name: string;
}

/** Fetch the authenticated user's own profile. */
export async function fetchMe(): Promise<UserMe> {
  const response = await apiClient.get<UserMe>("/users/me");
  return response.data;
}

/** Update the authenticated user's display name. */
export async function patchMe(update: UserMeUpdate): Promise<UserMe> {
  const response = await apiClient.patch<UserMe>("/users/me", update);
  return response.data;
}
