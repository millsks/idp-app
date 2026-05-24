/**
 * Module-level token and logout store.
 *
 * Shared between AuthContext (writes) and the Axios client (reads) to avoid a
 * circular import: AuthContext → auth.ts → client.ts → AuthContext.
 */

let _token: string | null = null;
let _logoutFn: (() => void) | null = null;

/** Read the current in-memory JWT (null when unauthenticated or after refresh). */
export const getAuthToken = (): string | null => _token;

/** Store or clear the in-memory JWT. Called only by AuthContext. */
export const setAuthToken = (t: string | null): void => {
  _token = t;
};

/** Register the logout function so the Axios 401 interceptor can call it. */
export const setLogoutCallback = (fn: () => void): void => {
  _logoutFn = fn;
};

/** Invoke the registered logout function (no-op if none registered yet). */
export const runLogout = (): void => {
  _logoutFn?.();
};
