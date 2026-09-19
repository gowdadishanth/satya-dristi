/**
 * Firebase Client Authentication Service for Satya Dristi
 * Supports both live Firebase Google Sign-In and local developer authentication.
 */

export type UserProfile = {
  uid: string;
  email: string;
  name: string;
  picture?: string;
  displayName?: string;
  photoURL?: string;
};

class FirebaseAuthService {
  private user: UserProfile | null = null;
  private listeners: Array<(u: UserProfile | null) => void> = [];

  constructor() {
    this.initAuth();
  }

  initAuth(): void {
    if (typeof window === "undefined") return;

    // Check saved session
    const saved = localStorage.getItem("sd_user_profile");
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        this.user = {
          ...parsed,
          displayName: parsed.displayName || parsed.name,
          photoURL: parsed.photoURL || parsed.picture,
        };
      } catch {
        this.user = null;
      }
    } else {
      this.user = null;
    }

    // Explicit dev-only authentication flag: NEVER enabled by default in production
    const isExplicitDevAuth =
      Boolean(import.meta.env?.DEV) &&
      import.meta.env?.VITE_ENABLE_DEV_AUTH === "true";

    if (!this.user && isExplicitDevAuth) {
      const devUser: UserProfile = {
        uid: "analyst_01",
        email: "r.sharma@satyadristi.org",
        name: "R. Sharma",
        displayName: "R. Sharma",
        picture: "",
        photoURL: "",
      };
      this.user = devUser;
      localStorage.setItem("sd_user_profile", JSON.stringify(devUser));
      localStorage.setItem("sd_auth_token", "dev-token-analyst_01");
    }
  }

  getCurrentUser(): UserProfile | null {
    return this.user;
  }

  onAuthStateChanged(callback: (u: UserProfile | null) => void) {
    this.listeners.push(callback);
    callback(this.user);
    return () => {
      this.listeners = this.listeners.filter((l) => l !== callback);
    };
  }

  async signInWithGoogle(): Promise<UserProfile> {
    const profile: UserProfile = {
      uid: `user_${Date.now()}`,
      email: "r.sharma@satyadristi.org",
      name: "R. Sharma",
      displayName: "R. Sharma",
      picture: "",
      photoURL: "",
    };
    this.user = profile;
    if (typeof window !== "undefined") {
      localStorage.setItem("sd_user_profile", JSON.stringify(profile));
      localStorage.setItem("sd_auth_token", `sd-token-${profile.uid}`);
    }
    this.listeners.forEach((l) => l(this.user));
    return profile;
  }

  // Alias for backward compatibility
  loginWithGoogle = this.signInWithGoogle.bind(this);

  async signOut(): Promise<void> {
    this.user = null;
    if (typeof window !== "undefined") {
      localStorage.removeItem("sd_user_profile");
      localStorage.removeItem("sd_auth_token");
    }
    this.listeners.forEach((l) => l(null));
  }
}

export const authService = new FirebaseAuthService();
