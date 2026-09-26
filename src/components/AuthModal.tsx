import { useState } from "react";
import { authService, type UserProfile } from "../lib/firebase";
import { IconClose, IconCheck, IconTriangle, IconSatellite } from "./icons";

export function GoogleIcon({ className = "h-5 w-5" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" aria-hidden="true">
      <path
        fill="#4285F4"
        d="M23.745 12.27c0-.7-.06-1.4-.19-2.07H12v4.51h6.6c-.29 1.52-1.14 2.82-2.4 3.68v3.05h3.88c2.27-2.09 3.665-5.17 3.665-9.17z"
      />
      <path
        fill="#34A853"
        d="M12 24c3.24 0 5.95-1.08 7.93-2.91l-3.88-3.05c-1.08.72-2.45 1.16-4.05 1.16-3.12 0-5.77-2.1-6.72-4.93H1.26v3.15C3.25 21.36 7.33 24 12 24z"
      />
      <path
        fill="#FBBC05"
        d="M5.28 14.27c-.25-.72-.38-1.49-.38-2.27s.13-1.55.38-2.27V6.58H1.26C.46 8.16 0 9.94 0 12s.46 3.84 1.26 5.42l4.02-3.15z"
      />
      <path
        fill="#EA4335"
        d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.95 1.19 15.24 0 12 0 7.33 0 3.25 2.64 1.26 6.58l4.02 3.15c.95-2.83 3.6-4.98 6.72-4.98z"
      />
    </svg>
  );
}

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: (user: UserProfile) => void;
}

export function AuthModal({ isOpen, onClose, onSuccess }: AuthModalProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [apiKeyInput, setApiKeyInput] = useState("");
  const [showApiKeyConfig, setShowApiKeyConfig] = useState(false);

  if (!isOpen) return null;

  const handleGoogleSignIn = async () => {
    try {
      setIsLoading(true);
      setError(null);

      if (apiKeyInput.trim()) {
        authService.initFirebase(apiKeyInput.trim());
      }

      const user = await authService.signInWithGoogle();
      if (onSuccess) {
        onSuccess(user);
      }
      onClose();
    } catch (err: any) {
      const msg = err?.message || "Google authentication failed.";
      setError(msg);
      if (msg.includes("VITE_FIREBASE_API_KEY") || msg.includes("API key")) {
        setShowApiKeyConfig(true);
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-150"
      onClick={onClose}
    >
      <div
        className="relative w-full max-w-md overflow-hidden rounded-xl border border-border bg-card text-card-foreground shadow-2xl animate-in zoom-in-95 duration-150"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border px-6 py-4">
          <div className="flex items-center gap-3">
            <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-gradient-to-br from-[#4dbe55] to-[#79ed91] text-[#081a0c] shadow-xs font-bold">
              <IconSatellite className="h-[18px] w-[18px]" />
            </span>
            <div className="flex flex-col justify-center">
              <h2 className="text-base font-semibold leading-tight text-foreground">Sign In</h2>
              <p className="text-[11px] text-muted-foreground leading-tight mt-0.5">Satya Dristi Earth Observation</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-md p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground focus-ring transition-colors"
            aria-label="Close"
          >
            <IconClose className="h-4 w-4" />
          </button>
        </div>

        {/* Body */}
        <div className="p-6 space-y-5">
          <div className="space-y-1">
            <h3 className="text-sm font-medium text-foreground">Authenticate with Google</h3>
            <p className="text-xs text-muted-foreground leading-relaxed">
              Google will prompt you to select an account. Your authenticated Firebase identity is verified directly by the Satya Dristi backend.
            </p>
          </div>

          {error && (
            <div className="flex items-start gap-2.5 rounded-lg border border-err/30 bg-err/10 p-3 text-xs text-err animate-in fade-in">
              <IconTriangle className="h-4 w-4 shrink-0 mt-0.5 text-err" />
              <div className="space-y-1">
                <span className="font-medium">{error}</span>
              </div>
            </div>
          )}

          {/* Real Google Auth Button */}
          <button
            type="button"
            onClick={handleGoogleSignIn}
            disabled={isLoading}
            className="w-full flex items-center justify-center gap-3 px-4 py-3 rounded-lg border border-[#223244] bg-[#131b26] text-[#f0f6fc] font-medium hover:bg-[#1a2535] hover:border-accent/50 shadow-md transition-all active:scale-[0.99] disabled:opacity-60 cursor-pointer"
          >
            {isLoading ? (
              <div className="flex items-center gap-2.5">
                <div className="h-4 w-4 rounded-full border-2 border-primary border-t-transparent animate-spin" />
                <span className="text-xs font-semibold text-muted-foreground">Connecting to Google...</span>
              </div>
            ) : (
              <>
                <GoogleIcon className="h-5 w-5" />
                <span className="text-sm font-semibold">Continue with Google</span>
              </>
            )}
          </button>

          {isLoading && (
            <p className="text-center text-[11.5px] text-muted-foreground animate-pulse">
              Please choose your Google Account in the opened popup window.
            </p>
          )}

          {/* Configuration prompt if Web API key is needed */}
          {showApiKeyConfig && (
            <div className="rounded-lg border border-border/80 bg-muted/30 p-3.5 space-y-2.5">
              <div className="text-xs font-semibold text-foreground">
                Firebase Web API Key Configuration
              </div>
              <p className="text-[11px] text-muted-foreground">
                Enter your project&apos;s Firebase Web API Key (from Firebase Console → Project settings → General → Web apps):
              </p>
              <div className="flex gap-2">
                <input
                  type="text"
                  placeholder="AIzaSy..."
                  value={apiKeyInput}
                  onChange={(e) => setApiKeyInput(e.target.value)}
                  className="flex-1 rounded border border-border bg-background px-2.5 py-1.5 text-xs font-mono focus-ring"
                />
                <button
                  type="button"
                  onClick={handleGoogleSignIn}
                  disabled={!apiKeyInput.trim() || isLoading}
                  className="rounded bg-primary text-primary-foreground px-3 py-1.5 text-xs font-medium hover:opacity-90 disabled:opacity-50"
                >
                  Save &amp; Retry
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="border-t border-border bg-muted/20 px-6 py-3 text-[11px] text-muted-foreground flex items-center justify-between">
          <span className="flex items-center gap-1.5">
            <IconCheck className="h-3.5 w-3.5 text-ok" />
            <span>Firebase Admin SDK &amp; Google Cloud Protected</span>
          </span>
          <span className="font-mono text-[10px]">v1.0.0</span>
        </div>
      </div>
    </div>
  );
}
