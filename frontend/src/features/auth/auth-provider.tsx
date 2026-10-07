"use client";

import { useQueryClient } from "@tanstack/react-query";
import {
  createContext,
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

import { apiClient, apiV1 } from "@/lib/api-client";
import { authStorage } from "@/lib/auth-storage";
import type { AuthResponse, User } from "@/types/auth";

export type AuthStatus = "loading" | "authenticated" | "unauthenticated";

interface AuthContextValue {
  status: AuthStatus;
  user: User | null;
  login: (email: string, password: string) => Promise<User>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<User | null>;
}

export const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [status, setStatus] = useState<AuthStatus>("loading");
  const queryClient = useQueryClient();

  const refreshUser = useCallback(async (): Promise<User | null> => {
    const token = authStorage.getAccess();
    if (!token) {
      setUser(null);
      setStatus("unauthenticated");
      return null;
    }
    try {
      const me = await apiClient.get<User>(apiV1("/auth/me"));
      setUser(me);
      setStatus("authenticated");
      return me;
    } catch {
      authStorage.clear();
      setUser(null);
      setStatus("unauthenticated");
      return null;
    }
  }, []);

  useEffect(() => {
    void refreshUser();
  }, [refreshUser]);

  const login = useCallback(
    async (email: string, password: string): Promise<User> => {
      const res = await apiClient.post<AuthResponse>(
        apiV1("/auth/login"),
        { email, password },
        { skipAuth: true },
      );
      authStorage.set(res.access_token, res.refresh_token);
      setUser(res.user);
      setStatus("authenticated");
      return res.user;
    },
    [],
  );

  const logout = useCallback(async (): Promise<void> => {
    const refresh = authStorage.getRefresh();
    try {
      if (refresh) {
        await apiClient.post(
          apiV1("/auth/logout"),
          { refresh_token: refresh },
          { skipAuth: true, skipRefresh: true },
        );
      }
    } catch {
      // ignore — we still clear client state
    } finally {
      authStorage.clear();
      setUser(null);
      setStatus("unauthenticated");
      queryClient.clear();
    }
  }, [queryClient]);

  const value = useMemo<AuthContextValue>(
    () => ({ status, user, login, logout, refreshUser }),
    [status, user, login, logout, refreshUser],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
