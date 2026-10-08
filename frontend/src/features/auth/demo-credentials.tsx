"use client";

import {
  Check,
  Copy,
  LogIn,
  Shield,
  User as UserIcon,
  Users,
  type LucideIcon,
} from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface DemoAccount {
  role: string;
  email: string;
  password: string;
  description: string;
  icon: LucideIcon;
  accent: string;
}

const DEMO_ACCOUNTS: DemoAccount[] = [
  {
    role: "Admin",
    email: "admin@smartdesk-demo.dev",
    password: "Demo123!",
    description: "Users, teams, SLAs, AI config, analytics.",
    icon: Shield,
    accent: "text-violet-600 dark:text-violet-400",
  },
  {
    role: "Agent",
    email: "agent1@smartdesk-demo.dev",
    password: "Demo123!",
    description: "Ticket queue, comments, assignment, AI copilot.",
    icon: Users,
    accent: "text-blue-600 dark:text-blue-400",
  },
  {
    role: "Customer",
    email: "customer@smartdesk-demo.dev",
    password: "Demo123!",
    description: "Customer portal — sees own tickets only.",
    icon: UserIcon,
    accent: "text-emerald-600 dark:text-emerald-400",
  },
];

interface DemoCredentialsProps {
  onUse: (email: string, password: string) => void;
  activeEmail?: string | null;
}

export function DemoCredentials({
  onUse,
  activeEmail,
}: DemoCredentialsProps) {
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  const handleCopy = async (email: string, password: string) => {
    try {
      await navigator.clipboard.writeText(`${email}\t${password}`);
      setCopiedKey(email);
      window.setTimeout(() => setCopiedKey(null), 1500);
    } catch {
      /* clipboard permission denied — silent */
    }
  };

  return (
    <Card className="border-dashed bg-muted/20">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm">Try the demo</CardTitle>
        <CardDescription className="text-xs">
          Portfolio project. Use any account below to explore with
          pre-seeded data.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <ul role="list" className="space-y-2">
          {DEMO_ACCOUNTS.map((account) => {
            const Icon = account.icon;
            const isActive = activeEmail === account.email;
            const isCopied = copiedKey === account.email;

            return (
              <li
                key={account.email}
                className={cn(
                  "rounded-md border bg-background px-3 py-2.5 transition-colors",
                  isActive && "border-primary/50 ring-1 ring-primary/20"
                )}
              >
                <div className="flex items-start gap-3">
                  <Icon
                    className={cn("mt-0.5 h-4 w-4 shrink-0", account.accent)}
                    aria-hidden="true"
                  />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <p className="text-sm font-medium">{account.role}</p>
                      {isActive ? (
                        <span className="rounded-full bg-primary/10 px-1.5 py-0.5 text-2xs font-medium text-primary">
                          Selected
                        </span>
                      ) : null}
                    </div>
                    <p className="mt-0.5 text-2xs text-muted-foreground">
                      {account.description}
                    </p>
                  </div>
                  <div className="flex shrink-0 items-center gap-1">
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon-sm"
                      aria-label={`Copy ${account.role} credentials`}
                      onClick={() =>
                        handleCopy(account.email, account.password)
                      }
                    >
                      {isCopied ? (
                        <Check
                          className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400"
                          aria-hidden="true"
                        />
                      ) : (
                        <Copy className="h-3.5 w-3.5" aria-hidden="true" />
                      )}
                    </Button>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      className="h-7 px-2 text-xs"
                      onClick={() => onUse(account.email, account.password)}
                    >
                      <LogIn className="h-3 w-3" aria-hidden="true" />
                      Use
                    </Button>
                  </div>
                </div>

                <dl className="mt-2 grid grid-cols-[64px_minmax(0,1fr)] gap-x-2 gap-y-0.5 pl-7 font-mono text-2xs text-muted-foreground">
                  <dt>Email</dt>
                  <dd className="truncate text-foreground">
                    {account.email}
                  </dd>
                  <dt>Password</dt>
                  <dd className="text-foreground">{account.password}</dd>
                </dl>
              </li>
            );
          })}
        </ul>
      </CardContent>
    </Card>
  );
}