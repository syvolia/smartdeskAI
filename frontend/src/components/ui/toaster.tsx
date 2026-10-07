"use client";

import {
  Toast,
  ToastDescription,
  ToastProvider,
  ToastTitle,
  ToastViewport,
} from "@/components/ui/toast";
import { useToastState } from "@/hooks/use-toast";

export function Toaster() {
  const { toasts, dismiss } = useToastState();

  return (
    <ToastProvider swipeDirection="right">
      {toasts.map((t) => (
        <Toast
          key={t.id}
          variant={t.variant}
          duration={t.duration}
          onOpenChange={(open) => {
            if (!open) dismiss(t.id);
          }}
        >
          <ToastTitle>{t.title}</ToastTitle>
          {t.description ? (
            <ToastDescription>{t.description}</ToastDescription>
          ) : null}
        </Toast>
      ))}
      <ToastViewport />
    </ToastProvider>
  );
}
