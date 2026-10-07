import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import { LoginForm } from "@/features/auth/login-form";
import { renderWithProviders } from "@/test/utils";

// Mock the auth hook so we're testing the form, not the provider.
const mockLogin = vi.fn();
vi.mock("@/hooks/use-auth", () => ({
  useAuth: () => ({ login: mockLogin }),
}));

// Mock router navigation.
const mockReplace = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: mockReplace, push: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

describe("LoginForm", () => {
  beforeEach(() => {
    mockLogin.mockReset();
    mockReplace.mockReset();
  });

  it("shows validation errors when submitted empty", async () => {
    renderWithProviders(<LoginForm />);
    await userEvent.click(screen.getByRole("button", { name: /sign in/i }));
    expect(await screen.findByText(/email is required/i)).toBeInTheDocument();
  });

  it("rejects a malformed email", async () => {
    renderWithProviders(<LoginForm />);
    await userEvent.type(screen.getByLabelText(/email/i), "not-an-email");
    await userEvent.type(screen.getByLabelText(/password/i), "whatever");
    await userEvent.click(screen.getByRole("button", { name: /sign in/i }));
    expect(await screen.findByText(/enter a valid email/i)).toBeInTheDocument();
  });

  it("calls login with the entered credentials and navigates", async () => {
    mockLogin.mockResolvedValue({
      id: "u1",
      email: "agent@example.test",
      role: "AGENT",
    });

    renderWithProviders(<LoginForm />);
    await userEvent.type(screen.getByLabelText(/email/i), "agent@example.test");
    await userEvent.type(screen.getByLabelText(/password/i), "StrongPassw0rd!");
    await userEvent.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith(
        "agent@example.test",
        "StrongPassw0rd!",
      );
    });
    expect(mockReplace).toHaveBeenCalledWith("/dashboard");
  });

  it("surfaces backend errors", async () => {
    const { ApiError } = await import("@/lib/api-client");
    mockLogin.mockRejectedValue(
      new ApiError("Invalid email or password.", 401),
    );

    renderWithProviders(<LoginForm />);
    await userEvent.type(screen.getByLabelText(/email/i), "a@b.test");
    await userEvent.type(screen.getByLabelText(/password/i), "wrong");
    await userEvent.click(screen.getByRole("button", { name: /sign in/i }));

    expect(
      await screen.findByText(/invalid email or password/i),
    ).toBeInTheDocument();
  });
});
