"use client";

import { Suspense, useState } from "react";

import { Skeleton } from "@/components/ui/skeleton";
import { DemoCredentials } from "@/features/auth/demo-credentials";
import { LoginForm } from "@/features/auth/login-form";

interface DemoDefaults {
  email: string;
  password: string;
  /** Bumped on each "Use" click to force LoginForm to remount with the
   *  new default values. */
  key: number;
}

function LoginFormFallback() {
  return (
    <div className="space-y-4" aria-hidden="true">
      <Skeleton className="h-4 w-12" />
      <Skeleton className="h-9 w-full" />
      <Skeleton className="h-4 w-16" />
      <Skeleton className="h-9 w-full" />
      <Skeleton className="h-9 w-full" />
    </div>
  );
}

export function LoginContent() {
  const [defaults, setDefaults] = useState<DemoDefaults>({
    email: "",
    password: "",
    key: 0,
  });

  const handleUse = (email: string, password: string) => {
    setDefaults((prev) => ({ email, password, key: prev.key + 1 }));
  };

  return (
    <div className="space-y-6">
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

      <Suspense fallback={<LoginFormFallback />}>
        <LoginForm
          key={defaults.key}
          defaultEmail={defaults.email}
          defaultPassword={defaults.password}
        />
      </Suspense>

      <DemoCredentials onUse={handleUse} activeEmail={defaults.email || null} />

      <p className="text-center text-xs text-muted-foreground">
        Need an account? Ask your administrator to invite you.
      </p>
    </div>
  );
}
