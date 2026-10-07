import { config } from "@/lib/config";

export function buildWebSocketUrl(token: string): string {
  // API base is http(s)://... ; WebSocket wants ws(s)://...
  const base = config.apiBaseUrl.replace(/^http/, "ws");
  const prefix = config.apiV1Prefix;
  return `${base}${prefix}/ws?token=${encodeURIComponent(token)}`;
}