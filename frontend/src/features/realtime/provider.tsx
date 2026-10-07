"use client";

import { useQueryClient } from "@tanstack/react-query";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import { notificationKeys } from "@/features/notifications/queries";
import { buildWebSocketUrl } from "@/features/realtime/socket-url";
import type { RealtimeEvent } from "@/features/realtime/types";
import { aiKeys } from "@/features/tickets/ai/queries";
import { ticketKeys } from "@/features/tickets/queries";
import { useAuth } from "@/hooks/use-auth";
import { authStorage } from "@/lib/auth-storage";

type Listener = (event: RealtimeEvent) => void;

interface RealtimeContextValue {
  subscribe: (listener: Listener) => () => void;
  isConnected: boolean;
}

const RealtimeContext = createContext<RealtimeContextValue>({
  subscribe: () => () => {},
  isConnected: false,
});

const MAX_SEEN_IDS = 200;
const MIN_RECONNECT_MS = 800;
const MAX_RECONNECT_MS = 30_000;
const PING_INTERVAL_MS = 25_000;

export function RealtimeProvider({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const listenersRef = useRef<Set<Listener>>(new Set());
  const seenIdsRef = useRef<string[]>([]);
  const [isConnected, setIsConnected] = useState(false);

  const subscribe = useCallback((listener: Listener) => {
    listenersRef.current.add(listener);
    return () => {
      listenersRef.current.delete(listener);
    };
  }, []);

  const hasSeen = useCallback((id: string) => {
    if (seenIdsRef.current.includes(id)) return true;
    seenIdsRef.current.push(id);
    if (seenIdsRef.current.length > MAX_SEEN_IDS) {
      seenIdsRef.current.splice(0, seenIdsRef.current.length - MAX_SEEN_IDS);
    }
    return false;
  }, []);

  useEffect(() => {
    if (!user) return;

    let stopped = false;
    let ws: WebSocket | null = null;
    let attempt = 0;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    let pingTimer: ReturnType<typeof setInterval> | null = null;

    const dispatch = (event: RealtimeEvent) => {
      if (hasSeen(event.id)) return;

      if (event.type === "notification.created") {
        queryClient.invalidateQueries({ queryKey: notificationKeys.all });
      }

      if (event.type.startsWith("ticket.")) {
        if (event.ticket_id) {
          queryClient.invalidateQueries({
            queryKey: ticketKeys.detail(event.ticket_id),
          });
          queryClient.invalidateQueries({
            queryKey: ticketKeys.comments(event.ticket_id),
          });
          queryClient.invalidateQueries({
            queryKey: ticketKeys.events(event.ticket_id),
          });
          queryClient.invalidateQueries({
            queryKey: aiKeys.suggestionsForTicket(event.ticket_id),
          });
        }
        queryClient.invalidateQueries({ queryKey: ticketKeys.lists() });
      }

      for (const listener of listenersRef.current) {
        try {
          listener(event);
        } catch {
          /* ignore listener errors */
        }
      }
    };

    const scheduleReconnect = () => {
      const base = Math.min(MAX_RECONNECT_MS, MIN_RECONNECT_MS * 2 ** attempt);
      const jitter = Math.random() * 400;
      attempt += 1;
      reconnectTimer = setTimeout(open, base + jitter);
    };

    const open = () => {
      if (stopped) return;
      const token = authStorage.getAccess();
      if (!token) return;

      try {
        ws = new WebSocket(buildWebSocketUrl(token));
      } catch {
        scheduleReconnect();
        return;
      }

      ws.onopen = () => {
        attempt = 0;
        setIsConnected(true);
        // On reconnect, invalidate everything so state converges with REST.
        queryClient.invalidateQueries();
        pingTimer = setInterval(() => {
          try {
            ws?.send(JSON.stringify({ kind: "ping" }));
          } catch {
            /* ignore */
          }
        }, PING_INTERVAL_MS);
      };

      ws.onmessage = (raw) => {
        try {
          const frame = JSON.parse(raw.data);
          if (frame.kind === "event" && frame.event) dispatch(frame.event);
        } catch {
          /* malformed frame */
        }
      };

      ws.onclose = () => {
        setIsConnected(false);
        if (pingTimer) {
          clearInterval(pingTimer);
          pingTimer = null;
        }
        if (!stopped) scheduleReconnect();
      };

      ws.onerror = () => {
        /* close handler will run */
      };
    };

    open();

    return () => {
      stopped = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      if (pingTimer) clearInterval(pingTimer);
      try {
        ws?.close();
      } catch {
        /* ignore */
      }
      setIsConnected(false);
    };
  }, [user?.id, queryClient, hasSeen]);

  const value = useMemo<RealtimeContextValue>(
    () => ({ subscribe, isConnected }),
    [subscribe, isConnected],
  );

  return (
    <RealtimeContext.Provider value={value}>
      {children}
    </RealtimeContext.Provider>
  );
}

export function useRealtime(): RealtimeContextValue {
  return useContext(RealtimeContext);
}
