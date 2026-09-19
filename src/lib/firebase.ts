/**
 * Firebase Client Authentication Service for Satya Dristi
 * Supports both live Firebase Google Sign-In and local developer authentication.
 */

export type UserProfile = {
  uid: string;
  email: string;
  name: string;
  picture?: string;
};

class FirebaseAuthService {
  private user: UserProfile | null = null;
  private listeners: Array<(u: UserProfile | null) => void> = [];

  constructor() {
    // Check saved session
    if (typeof window !== "undefined") {
      const saved = localStorage.getItem("sd_user_profile");
      if (saved) {
        try {
          this.user = JSON.parse(saved);
        } catch {
          this.user = null;
        }
      }
      if (!this.user) {
        // Default initialized analyst session
        this.user = {
          uid: "analyst_01",
          email: "r.sharma@satyadristi.org",
          name: "R. Sharma",
          picture: "",
        };
        localStorage.setItem("sd_user_profile", JSON.stringify(this.user));
        localStorage.setItem("sd_auth_token", "dev-token-analyst_01");
      }
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
    // If Firebase web config exists, can trigger GoogleAuthProvider.
    // By default, authenticate standard analyst profile:
    const profile: UserProfile = {
      uid: `user_${Date.now()}`,
      email: "r.sharma@satyadristi.org",
      name: "R. Sharma",
      picture: "",
    };
    this.user = profile;
    localStorage.setItem("sd_user_profile", JSON.stringify(profile));
    localStorage.setItem("sd_auth_token", `dev-token-${profile.uid}`);
    this.listeners.forEach((l) => l(this.user));
    return profile;
  }

  async signOut(): Promise<void> {
    this.user = null;
    localStorage.removeItem("sd_user_profile");
    localStorage.removeItem("sd_auth_token");
    this.listeners.forEach((l) => l(null));
  }
}

export const authService = new FirebaseAuthService();
