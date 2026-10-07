"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";

import { Toaster } from "@/components/ui/toaster";
import { AuthProvider } from "@/features/auth/auth-provider";
import { RealtimeProvider } from "@/features/realtime/provider";
import { ToastProviderInternal } from "@/hooks/use-toast";

export function Providers({ children }: { children: ReactNode }) {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 30_000,
            retry: 1,
            refetchOnWindowFocus: false,
          },
        },
      })
  );

  return (
    <QueryClientProvider client={client}>
      <ToastProviderInternal>
        <AuthProvider>
          <RealtimeProvider>{children}</RealtimeProvider>
        </AuthProvider>
        <Toaster />
      </ToastProviderInternal>
    </QueryClientProvider>
  );
}