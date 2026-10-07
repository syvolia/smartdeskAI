import type { Metadata } from "next";

import { LoginForm } from "@/features/auth/login-form";

export const metadata: Metadata = {
  title: "Sign in",
};

export default function LoginPage() {
  return (
    <div className="space-y-8">
      <div className="flex flex-col items-center text-center">
        <span
          aria-hidden="true"
          className="mb-4 flex h-10 w-10 items-center justify-center rounded-lg bg-primary text-primary-foreground"
        >
          <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none">
            <path
              d="M4 7a3 3 0 0 1 3-3h10a3 3 0 0 1 3 3v6a3 3 0 0 1-3 3H9l-5 4V7Z"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinejoin="round"
            />
          </svg>
        </span>
        <h1 className="text-xl font-semibold tracking-tight">
          Sign in to SmartDesk AI
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Enter your credentials to access your workspace.
        </p>
      </div>

      <LoginForm />

      <p className="text-center text-xs text-muted-foreground">
        Need an account? Ask your administrator to invite you.
      </p>
    </div>
  );
}
