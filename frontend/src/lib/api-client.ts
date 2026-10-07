"use client";

import { authStorage } from "@/lib/auth-storage";
import { config } from "@/lib/config";

export interface ApiErrorBody {
  error: {
    code: string;
    message: string;
    details?: unknown;
  };
}

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details?: unknown;

  constructor(
    message: string,
    status: number,
    code = "unknown_error",
    details?: unknown
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

type QueryValue = string | number | boolean | undefined | null;

export interface RequestOptions extends Omit<RequestInit, "body"> {
  json?: unknown;
  query?: Record<string, QueryValue>;
  /** Skip auth header + refresh logic (used by /auth/* endpoints). */
  skipAuth?: boolean;
  /** Skip automatic refresh on 401 (used for the refresh call itself). */
  skipRefresh?: boolean;
}

function buildUrl(path: string, query?: RequestOptions["query"]): string {
  const base = path.startsWith("http")
    ? path
    : `${config.apiBaseUrl}${path.startsWith("/") ? path : `/${path}`}`;
  const url = new URL(base);
  if (query) {
    for (const [key, value] of Object.entries(query)) {
      if (value !== undefined && value !== null) {
        url.searchParams.set(key, String(value));
      }
    }
  }
  return url.toString();
}

function isApiErrorBody(value: unknown): value is ApiErrorBody {
  return (
    typeof value === "object" &&
    value !== null &&
    "error" in value &&
    typeof (value as { error: unknown }).error === "object"
  );
}

let refreshPromise: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  if (refreshPromise) return refreshPromise;

  refreshPromise = (async () => {
    const refresh = authStorage.getRefresh();
    if (!refresh) return null;

    try {
      const res = await fetch(
        `${config.apiBaseUrl}${config.apiV1Prefix}/auth/refresh`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json", Accept: "application/json" },
          body: JSON.stringify({ refresh_token: refresh }),
        }
      );
      if (!res.ok) {
        authStorage.clear();
        return null;
      }
      const data = (await res.json()) as {
        access_token: string;
        refresh_token: string;
      };
      authStorage.set(data.access_token, data.refresh_token);
      return data.access_token;
    } catch {
      authStorage.clear();
      return null;
    } finally {
      refreshPromise = null;
    }
  })();

  return refreshPromise;
}

async function rawFetch(
  path: string,
  options: RequestOptions,
  token: string | null
): Promise<Response> {
  const { json, query, headers, skipAuth, skipRefresh, ...rest } = options;
  void skipRefresh;

  const finalHeaders: Record<string, string> = {
    Accept: "application/json",
    ...(json !== undefined ? { "Content-Type": "application/json" } : {}),
  };

  if (!skipAuth && token) {
    finalHeaders.Authorization = `Bearer ${token}`;
  }

  if (headers) {
    new Headers(headers).forEach((value, key) => {
      finalHeaders[key] = value;
    });
  }

  return fetch(buildUrl(path, query), {
    ...rest,
    headers: finalHeaders,
    body: json !== undefined ? JSON.stringify(json) : undefined,
    cache: "no-store",
  });
}

export async function apiFetch<T>(
  path: string,
  options: RequestOptions = {}
): Promise<T> {
  const token = options.skipAuth ? null : authStorage.getAccess();

  let response = await rawFetch(path, options, token);

  if (
    response.status === 401 &&
    !options.skipAuth &&
    !options.skipRefresh &&
    typeof window !== "undefined"
  ) {
    const newToken = await refreshAccessToken();
    if (newToken) {
      response = await rawFetch(path, options, newToken);
    }
  }

  const contentType = response.headers.get("content-type") ?? "";
  const isJson = contentType.includes("application/json");
  const payload: unknown = isJson
    ? await response.json()
    : await response.text();

  if (!response.ok) {
    if (isApiErrorBody(payload)) {
      throw new ApiError(
        payload.error.message,
        response.status,
        payload.error.code,
        payload.error.details
      );
    }
    throw new ApiError(
      `Request failed with status ${response.status}`,
      response.status
    );
  }

  return payload as T;
}

export const apiClient = {
  get: <T>(path: string, options?: RequestOptions) =>
    apiFetch<T>(path, { ...options, method: "GET" }),
  post: <T>(path: string, json?: unknown, options?: RequestOptions) =>
    apiFetch<T>(path, { ...options, method: "POST", json }),
  patch: <T>(path: string, json?: unknown, options?: RequestOptions) =>
    apiFetch<T>(path, { ...options, method: "PATCH", json }),
  put: <T>(path: string, json?: unknown, options?: RequestOptions) =>
    apiFetch<T>(path, { ...options, method: "PUT", json }),
  delete: <T>(path: string, options?: RequestOptions) =>
    apiFetch<T>(path, { ...options, method: "DELETE" }),
};

export const apiV1 = (path: string) =>
  `${config.apiV1Prefix}${path.startsWith("/") ? path : `/${path}`}`;