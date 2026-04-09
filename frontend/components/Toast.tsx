"use client";

import { useState, useCallback, useEffect, useRef } from "react";

// ─── Types ────────────────────────────────────────────────────────────────────

export type ToastType = "success" | "error" | "info";

interface Toast {
  id: string;
  message: string;
  type: ToastType;
  /** Whether the toast is in the process of being removed (fade-out) */
  exiting: boolean;
}

// ─── Style maps ───────────────────────────────────────────────────────────────

const containerStyles: Record<ToastType, string> = {
  success:
    "bg-white border border-green-200 text-green-800 shadow-sm",
  error:
    "bg-white border border-red-200 text-red-800 shadow-sm",
  info:
    "bg-white border border-blue-200 text-blue-800 shadow-sm",
};

const iconStyles: Record<ToastType, string> = {
  success: "text-green-500",
  error:   "text-red-500",
  info:    "text-blue-500",
};

const progressStyles: Record<ToastType, string> = {
  success: "bg-green-400",
  error:   "bg-red-400",
  info:    "bg-blue-400",
};

// ─── Icons ────────────────────────────────────────────────────────────────────

function SuccessIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      className="h-5 w-5 flex-shrink-0"
      viewBox="0 0 20 20"
      fill="currentColor"
      aria-hidden="true"
    >
      <path
        fillRule="evenodd"
        d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
        clipRule="evenodd"
      />
    </svg>
  );
}

function ErrorIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      className="h-5 w-5 flex-shrink-0"
      viewBox="0 0 20 20"
      fill="currentColor"
      aria-hidden="true"
    >
      <path
        fillRule="evenodd"
        d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
        clipRule="evenodd"
      />
    </svg>
  );
}

function InfoIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      className="h-5 w-5 flex-shrink-0"
      viewBox="0 0 20 20"
      fill="currentColor"
      aria-hidden="true"
    >
      <path
        fillRule="evenodd"
        d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
        clipRule="evenodd"
      />
    </svg>
  );
}

const ICONS: Record<ToastType, React.ReactNode> = {
  success: <SuccessIcon />,
  error:   <ErrorIcon />,
  info:    <InfoIcon />,
};

const LABELS: Record<ToastType, string> = {
  success: "Success",
  error:   "Error",
  info:    "Info",
};

// ─── Auto-dismiss duration (ms) ───────────────────────────────────────────────
const DISMISS_DURATION = 3000;
/** How long the slide-out / fade-out animation plays before the item is removed from state */
const EXIT_ANIMATION_DURATION = 350;

// ─── Module-level singleton so useToast can be called in any component ────────

type Listener = (toasts: Toast[]) => void;

let _toasts: Toast[] = [];
const _listeners = new Set<Listener>();

function notify() {
  _listeners.forEach((l) => l([..._toasts]));
}

function addToast(message: string, type: ToastType) {
  const id = `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
  _toasts = [..._toasts, { id, message, type, exiting: false }];
  notify();

  // Schedule auto-dismiss
  setTimeout(() => removeToast(id), DISMISS_DURATION);
}

function removeToast(id: string) {
  // Mark as exiting first (triggers CSS fade-out / slide-out)
  _toasts = _toasts.map((t) =>
    t.id === id ? { ...t, exiting: true } : t
  );
  notify();

  // Remove from list after animation completes
  setTimeout(() => {
    _toasts = _toasts.filter((t) => t.id !== id);
    notify();
  }, EXIT_ANIMATION_DURATION);
}

// ─── Hook ─────────────────────────────────────────────────────────────────────

export function useToast() {
  const showToast = useCallback(
    (message: string, type: ToastType = "info") => {
      addToast(message, type);
    },
    []
  );

  return { showToast };
}

// ─── Individual toast item ────────────────────────────────────────────────────

interface ToastItemProps {
  toast: Toast;
}

function ToastItem({ toast }: ToastItemProps) {
  const { id, message, type, exiting } = toast;

  return (
    <div
      role="alert"
      aria-live="assertive"
      aria-atomic="true"
      className={[
        // Layout
        "relative flex items-start gap-3 w-80 max-w-[calc(100vw-2rem)]",
        "rounded-xl px-4 py-3 overflow-hidden",
        // Colors
        containerStyles[type],
        // Animation: slide in from right on mount, slide out + fade on exit
        "transition-all duration-350 ease-in-out",
        exiting
          ? "opacity-0 translate-x-10 scale-95"
          : "opacity-100 translate-x-0 scale-100",
      ].join(" ")}
    >
      {/* Type icon */}
      <span className={`mt-0.5 ${iconStyles[type]}`}>
        {ICONS[type]}
      </span>

      {/* Text */}
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold leading-snug">
          {LABELS[type]}
        </p>
        <p className="text-sm leading-snug break-words mt-0.5 font-normal opacity-90">
          {message}
        </p>
      </div>

      {/* Dismiss button */}
      <button
        onClick={() => removeToast(id)}
        aria-label="Dismiss notification"
        className={[
          "flex-shrink-0 -mt-0.5 -mr-1 p-1 rounded-lg",
          "opacity-50 hover:opacity-100 focus:opacity-100",
          "transition-opacity focus:outline-none focus-visible:ring-2",
          type === "success" ? "focus-visible:ring-green-400" : "",
          type === "error"   ? "focus-visible:ring-red-400"   : "",
          type === "info"    ? "focus-visible:ring-blue-400"  : "",
        ].join(" ")}
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          className="h-4 w-4"
          viewBox="0 0 20 20"
          fill="currentColor"
          aria-hidden="true"
        >
          <path
            fillRule="evenodd"
            d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
            clipRule="evenodd"
          />
        </svg>
      </button>

      {/* Progress bar — shrinks from full width to 0 over DISMISS_DURATION */}
      <ProgressBar type={type} />
    </div>
  );
}

// ─── Animated progress bar ────────────────────────────────────────────────────

function ProgressBar({ type }: { type: ToastType }) {
  const barRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = barRef.current;
    if (!el) return;

    // Start at full width, animate to 0 over DISMISS_DURATION
    el.style.transition = "none";
    el.style.width = "100%";

    // Force reflow so the browser registers the initial state
    void el.offsetWidth;

    el.style.transition = `width ${DISMISS_DURATION}ms linear`;
    el.style.width = "0%";
  }, []);

  return (
    <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-black/5">
      <div
        ref={barRef}
        className={`h-full ${progressStyles[type]} opacity-60`}
      />
    </div>
  );
}

// ─── Container ────────────────────────────────────────────────────────────────

export function ToastContainer() {
  const [toasts, setToasts] = useState<Toast[]>([]);

  useEffect(() => {
    // Register this component as a listener
    const listener: Listener = (updated) => setToasts(updated);
    _listeners.add(listener);

    // Sync with any toasts already in flight
    setToasts([..._toasts]);

    return () => {
      _listeners.delete(listener);
    };
  }, []);

  if (toasts.length === 0) return null;

  return (
    <div
      aria-label="Notifications"
      className="fixed top-4 right-4 z-50 flex flex-col gap-2 items-end pointer-events-none"
    >
      {toasts.map((toast) => (
        // pointer-events-auto restores interactivity for each toast
        <div key={toast.id} className="pointer-events-auto">
          <ToastItem toast={toast} />
        </div>
      ))}
    </div>
  );
}
