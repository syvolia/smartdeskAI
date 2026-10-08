import type { Metadata } from "next";

import { LoginContent } from "@/features/auth/login-content";

export const metadata: Metadata = {
  title: "Sign in",
};

export default function LoginPage() {
  return <LoginContent />;
}
