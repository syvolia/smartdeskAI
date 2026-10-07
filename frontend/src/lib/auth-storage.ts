"use client";

/**
 * Token storage abstraction.
 *
 * Uses localStorage for the portfolio build so the app runs without a
 * cookie-based session backend. In production with cookie auth, swap
 * this module for a server-managed session and delete the tokens from
 * the client entirely.
 */

const ACCESS_KEY = "smartdesk.access_token";
const REFRESH_KEY = "smartdesk.refresh_token";

export const authStorage = {
  getAccess(): string | null {
    if (typeof window === "undefined") return null;
    return window.localStorage.getItem(ACCESS_KEY);
  },
  getRefresh(): string | null {
    if (typeof window === "undefined") return null;
    return window.localStorage.getItem(REFRESH_KEY);
  },
  set(access: string, refresh: string): void {
    if (typeof window === "undefined") return;
    window.localStorage.setItem(ACCESS_KEY, access);
    window.localStorage.setItem(REFRESH_KEY, refresh);
  },
  clear(): void {
    if (typeof window === "undefined") return;
    window.localStorage.removeItem(ACCESS_KEY);
    window.localStorage.removeItem(REFRESH_KEY);
  },
};