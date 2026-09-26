import { initializeApp, getApps, getApp, type FirebaseApp } from "firebase/app";
import { getAnalytics, isSupported } from "firebase/analytics";
import {
  getAuth,
  GoogleAuthProvider,
  signInWithPopup,
  signOut as fbSignOut,
  onAuthStateChanged as fbOnAuthStateChanged,
  onIdTokenChanged as fbOnIdTokenChanged,
  type User as FirebaseUser,
  type Auth,
} from "firebase/auth";

export type UserProfile = {
  uid: string;
  email: string;
  name: string;
  displayName?: string;
  photoURL?: string;
  picture?: string;
};

// Official Satya Dristi Firebase Web App Configuration
export const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY || "",
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN || "satya-dristi.firebaseapp.com",
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID || "satya-dristi",
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET || "satya-dristi.firebasestorage.app",
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID || "1002567635352",
  appId: import.meta.env.VITE_FIREBASE_APP_ID || "1:1002567635352:web:27e8f49f460776e2cf5bed",
  measurementId: import.meta.env.VITE_FIREBASE_MEASUREMENT_ID || "G-5ZPKTF6NKC",
};

export function isJwtExpired(token: string | null, bufferSeconds = 60): boolean {
  if (!token || typeof token !== "string") return true;
  if (token.startsWith("dev-") || token.startsWith("test-") || token.startsWith("sd-")) {
    return false;
  }
  try {
    const parts = token.split(".");
    if (parts.length < 2) return false;
    const base64Url = parts[1];
    const base64 = base64Url.replace(/-/g, "+").replace(/_/g, "/");
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split("")
        .map((c) => "%" + ("00" + c.charCodeAt(0).toString(16)).slice(-2))
        .join("")
    );
    const parsed = JSON.parse(jsonPayload);
    if (typeof parsed.exp === "number") {
      return parsed.exp * 1000 <= Date.now() + bufferSeconds * 1000;
    }
  } catch {
    // If parsing fails, do not assume expired
  }
  return false;
}

export class FirebaseAuthService {
  private app: FirebaseApp | null = null;
  private auth: Auth | null = null;
  private user: UserProfile | null = null;
  private listeners: Array<(u: UserProfile | null) => void> = [];

  constructor() {
    this.initFirebase();
  }

  public initFirebase(customApiKey?: string): void {
    if (typeof window === "undefined") return;

    if (customApiKey) {
      firebaseConfig.apiKey = customApiKey;
      localStorage.setItem("sd_firebase_api_key", customApiKey);
    }

    try {
      if (getApps().length > 0) {
        this.app = getApp();
      } else if (firebaseConfig.apiKey) {
        this.app = initializeApp(firebaseConfig);
      } else {
        // Initialize with default project config if apiKey is provided
        this.app = initializeApp(firebaseConfig);
      }

      this.auth = getAuth(this.app);

      // Initialize Firebase Analytics if supported in browser environment
      if (typeof window !== "undefined" && firebaseConfig.measurementId) {
        isSupported().then((supported) => {
          if (supported && this.app) {
            getAnalytics(this.app);
          }
        }).catch(() => {});
      }

      // Listen to real Firebase Auth state changes
      fbOnAuthStateChanged(this.auth, async (fbUser: FirebaseUser | null) => {
        if (fbUser) {
          try {
            const token = await fbUser.getIdToken();
            localStorage.setItem("sd_auth_token", token);
          } catch {
            // Ignore token fetch error on init
          }
          const profile = this.mapUser(fbUser);
          this.user = profile;
          localStorage.setItem("sd_user_profile", JSON.stringify(profile));
          this.notifyListeners(profile);
        } else {
          this.user = null;
          localStorage.removeItem("sd_auth_token");
          localStorage.removeItem("sd_user_profile");
          this.notifyListeners(null);
        }
      });

      // Keep Firebase ID token fresh on token rotation
      fbOnIdTokenChanged(this.auth, async (fbUser: FirebaseUser | null) => {
        if (fbUser) {
          try {
            const token = await fbUser.getIdToken();
            localStorage.setItem("sd_auth_token", token);
          } catch {
            // Ignore
          }
        } else {
          localStorage.removeItem("sd_auth_token");
        }
      });
    } catch (err) {
      console.warn("Firebase client initialization status:", err);
    }
  }

  private mapUser(fbUser: FirebaseUser): UserProfile {
    const displayName =
      fbUser.displayName ||
      (fbUser.email ? fbUser.email.split("@")[0] : "Google User");
    return {
      uid: fbUser.uid,
      email: fbUser.email || "",
      name: displayName,
      displayName: displayName,
      photoURL: fbUser.photoURL || undefined,
      picture: fbUser.photoURL || undefined,
    };
  }

  getCurrentUser(): UserProfile | null {
    return this.user;
  }

  async getIdToken(forceRefresh = false): Promise<string | null> {
    if (this.auth) {
      try {
        if (typeof (this.auth as any).authStateReady === "function") {
          await Promise.race([
            (this.auth as any).authStateReady(),
            new Promise((r) => setTimeout(r, 1500)),
          ]);
        }
      } catch {
        // Fallback gracefully
      }

      if (this.auth.currentUser) {
        try {
          const token = await this.auth.currentUser.getIdToken(forceRefresh);
          if (token) {
            localStorage.setItem("sd_auth_token", token);
            return token;
          }
        } catch (tokenErr) {
          console.warn("Failed to get fresh ID token from currentUser:", tokenErr);
        }
      }
    }

    if (typeof window !== "undefined") {
      const cached = localStorage.getItem("sd_auth_token");
      if (cached) {
        if (!isJwtExpired(cached, 0)) {
          return cached;
        }
        // Cached token is definitely expired and currentUser is not available
        console.warn("Cached Firebase token expired. Clearing from storage.");
        localStorage.removeItem("sd_auth_token");
      }
    }
    return null;
  }

  onAuthStateChanged(callback: (u: UserProfile | null) => void): () => void {
    this.listeners.push(callback);
    callback(this.user);
    return () => {
      this.listeners = this.listeners.filter((l) => l !== callback);
    };
  }

  private notifyListeners(u: UserProfile | null): void {
    this.listeners.forEach((cb) => {
      try {
        cb(u);
      } catch (err) {
        console.error("Auth listener callback error:", err);
      }
    });
  }

  /**
   * Real Google Authentication using Firebase Web SDK.
   * Forces account selection so the user can choose or switch between Google accounts.
   */
  async signInWithGoogle(): Promise<UserProfile> {
    if (!this.auth) {
      this.initFirebase();
    }
    if (!this.auth) {
      throw new Error(
        "Firebase Authentication is not initialized. Please ensure VITE_FIREBASE_API_KEY is configured in your .env file."
      );
    }

    // Requirement 1 & 2: GoogleAuthProvider with prompt: "select_account"
    const provider = new GoogleAuthProvider();
    provider.setCustomParameters({
      prompt: "select_account",
    });

    try {
      const result = await signInWithPopup(this.auth, provider);
      const fbUser = result.user;
      const token = await fbUser.getIdToken();
      localStorage.setItem("sd_auth_token", token);
      const profile = this.mapUser(fbUser);
      this.user = profile;
      localStorage.setItem("sd_user_profile", JSON.stringify(profile));
      this.notifyListeners(profile);
      return profile;
    } catch (err: any) {
      const code = err?.code || "";
      if (code === "auth/popup-closed-by-user") {
        throw new Error("Google sign-in popup was closed before selecting an account.");
      }
      if (code === "auth/popup-blocked") {
        throw new Error(
          "Google sign-in popup was blocked by your browser. Please allow popups for localhost:8443 and try again."
        );
      }
      if (code === "auth/account-exists-with-different-credential") {
        throw new Error(
          "An account already exists with the same email address but different sign-in credentials."
        );
      }
      if (code === "auth/cancelled-popup-request") {
        throw new Error("Previous Google sign-in popup request was cancelled.");
      }
      if (code === "auth/network-request-failed") {
        throw new Error(
          "Network connection failed during Google sign-in. Please check your network connection."
        );
      }
      if (code === "auth/invalid-api-key" || code === "auth/api-key-not-valid") {
        throw new Error(
          "Firebase Web API key is invalid or missing. Please configure VITE_FIREBASE_API_KEY in your .env file."
        );
      }
      throw new Error(err?.message || "Google authentication failed.");
    }
  }

  // Alias for backward compatibility
  loginWithGoogle = this.signInWithGoogle.bind(this);

  async signOut(): Promise<void> {
    if (this.auth) {
      try {
        await fbSignOut(this.auth);
      } catch (err) {
        console.warn("Firebase sign-out warning:", err);
      }
    }
    this.user = null;
    if (typeof window !== "undefined") {
      localStorage.removeItem("sd_auth_token");
      localStorage.removeItem("sd_user_profile");
      sessionStorage.setItem("sd_explicit_sign_out", "true");
    }
    this.notifyListeners(null);
  }
}

export const authService = new FirebaseAuthService();
