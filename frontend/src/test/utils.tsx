import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, type RenderOptions } from "@testing-library/react";
import type { ReactElement, ReactNode } from "react";

import { ToastProviderInternal } from "@/hooks/use-toast";
import type { User } from "@/types/auth";

interface RenderWithProvidersOptions extends Omit<RenderOptions, "wrapper"> {
  queryClient?: QueryClient;
  user?: User | null;
}

/**
 * Test-only provider tree.
 *
 * We deliberately do NOT mount RealtimeProvider here — it opens a
 * WebSocket, which is meaningless in a jsdom test. Components that
 * depend on it use the default context value (isConnected: false) and
 * behave correctly.
 *
 * Similarly, we mount our own QueryClient rather than the app's, so
 * each test starts with a fresh cache.
 */
export function renderWithProviders(
  ui: ReactElement,
  options: RenderWithProvidersOptions = {}
) {
  const {
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    }),
    ...rest
  } = options;

  function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <ToastProviderInternal>{children}</ToastProviderInternal>
      </QueryClientProvider>
    );
  }

  return {
    queryClient,
    ...render(ui, { wrapper: Wrapper, ...rest }),
  };
}