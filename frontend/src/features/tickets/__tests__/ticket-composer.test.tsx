import { QueryClient } from "@tanstack/react-query";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { vi } from "vitest";

import { TicketComposer } from "@/features/tickets/ticket-composer";
import { renderWithProviders } from "@/test/utils";

const server = setupServer();
beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

// Mock auth storage so the API client attaches a token.
vi.mock("@/lib/auth-storage", () => ({
  authStorage: {
    getAccess: () => "fake-token",
    getRefresh: () => null,
    set: vi.fn(),
    clear: vi.fn(),
  },
}));

describe("TicketComposer", () => {
  it("posts a public reply and clears the textarea", async () => {
    let captured: any = null;
    server.use(
      http.post(
        "http://localhost:8000/api/v1/tickets/abc/comments",
        async ({ request }) => {
          captured = await request.json();
          return HttpResponse.json(
            {
              id: "c1",
              organization_id: "o1",
              ticket_id: "abc",
              author: null,
              body: captured.body,
              is_internal: captured.is_internal,
              created_at: new Date().toISOString(),
              updated_at: new Date().toISOString(),
            },
            { status: 201 },
          );
        },
      ),
    );

    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });

    renderWithProviders(<TicketComposer ticketId="abc" />, { queryClient });

    const textarea = screen.getByLabelText(/reply/i);
    await userEvent.type(textarea, "Thanks for reaching out.");
    await userEvent.click(screen.getByRole("button", { name: /send reply/i }));

    await waitFor(() => {
      expect(captured).toEqual({
        body: "Thanks for reaching out.",
        is_internal: false,
      });
    });
    await waitFor(() => expect(textarea).toHaveValue(""));
  });

  it("posts an internal note when the Internal tab is active", async () => {
    let captured: any = null;
    server.use(
      http.post(
        "http://localhost:8000/api/v1/tickets/abc/comments",
        async ({ request }) => {
          captured = await request.json();
          return HttpResponse.json(
            {
              id: "c2",
              organization_id: "o1",
              ticket_id: "abc",
              author: null,
              body: captured.body,
              is_internal: true,
              created_at: new Date().toISOString(),
              updated_at: new Date().toISOString(),
            },
            { status: 201 },
          );
        },
      ),
    );

    renderWithProviders(<TicketComposer ticketId="abc" />);

    await userEvent.click(screen.getByRole("tab", { name: /internal note/i }));
    await userEvent.type(
      screen.getByLabelText(/internal note/i),
      "Escalating to Tier 2.",
    );
    await userEvent.click(screen.getByRole("button", { name: /add note/i }));

    await waitFor(() => {
      expect(captured).toEqual({
        body: "Escalating to Tier 2.",
        is_internal: true,
      });
    });
  });

  it("disables submit when the textarea is empty", () => {
    renderWithProviders(<TicketComposer ticketId="abc" />);
    expect(screen.getByRole("button", { name: /send reply/i })).toBeDisabled();
  });
});
