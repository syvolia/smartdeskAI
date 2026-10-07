"use client";

import { useEffect } from "react";

import { useRealtime } from "@/features/realtime/provider";
import type { RealtimeEvent, RealtimeEventType } from "@/features/realtime/types";

export function useRealtimeEvent(
  types: RealtimeEventType[] | "any",
  handler: (event: RealtimeEvent) => void
): void {
  const { subscribe } = useRealtime();

  useEffect(() => {
    const isAny = types === "any";
    const set = isAny ? null : new Set(types);
    const unsubscribe = subscribe((event) => {
      if (isAny || set?.has(event.type)) handler(event);
    });
    return unsubscribe;
  }, [subscribe, handler, types]);
}