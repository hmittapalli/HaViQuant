import { useEffect, useState, type ReactNode } from "react";

type Props = {
  children: ReactNode;
};

type AuthUser = {
  authenticated: boolean;
  username: string;
};

const TOKEN_KEY = "haviquant_access_token";

const API = (
  (import.meta as unknown as {
    env?: { VITE_API_URL?: string };
  }).env?.VITE_API_URL ||
  "http://127.0.0.1:8000/api/v1"
).replace(/\/$/, "");

export function getAuthToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setAuthToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearAuthToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

export async function authFetch(
  path: string,
  options: RequestInit = {}
): Promise<Response> {
  const token = getAuthToken();

  const headers = new Headers(options.headers);

  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  return fetch(`${API}${path}`, {
    ...options,
    headers,
  });
}

export default function AuthGate({ children }: Props) {
  const [token, setToken] = useState<string | null>(getAuthToken());
  const [user, setUser] = useState<AuthUser | null>(null);
  const [checking, setChecking] = useState(!!token);

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!token) {
      setChecking(false);
      setUser(null);
      return;
    }

    let cancelled = false;

    setChecking(true);

    authFetch("/auth/me")
      .then(async (response) => {
        if (!response.ok) {
          throw new Error("Your session has expired.");
        }

        return response.json();
      })
      .then((data: AuthUser) => {
        if (!cancelled) {
          setUser(data);
        }
      })
      .catch(() => {
        if (!cancelled) {
          clearAuthToken();
          setToken(null);
          setUser(null);
        }
      })
      .finally(() => {
        if (!cancelled) {
          setChecking(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [token]);

  const login = async () => {
    const cleanUsername = username.trim();

    if (!cleanUsername || !password) {
      setError("Please enter your username and password.");
      return;
    }

    setBusy(true);
    setError("");

    try {
      const response = await fetch(`${API}/auth/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          username: cleanUsername,
          password,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data?.detail || "Invalid username or password.");
      }

      if (!data?.access_token) {
        throw new Error("Login succeeded but no access token was returned.");
      }

      setAuthToken(data.access_token);
      setToken(data.access_token);
      setPassword("");
    } catch (e: any) {
      setError(e?.message || "Unable to sign in.");
    } finally {
      setBusy(false);
    }
  };

  if (checking) {
    return (
      <div className="auth-screen">
        <div className="auth-card">
          <div className="logo">HQ</div>
          <h1>HaViQuant</h1>
          <p>Checking secure session...</p>
        </div>
      </div>
    );
  }

  if (token && user) {
    return <>{children}</>;
  }

  return (
    <div className="auth-screen">
      <div className="auth-card">
        <div className="logo">HQ</div>

        <h1>HaViQuant</h1>

        <p>Private Portfolio Access</p>

        <input
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          placeholder="Username"
          autoComplete="username"
          disabled={busy}
        />

        <input
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Password"
          type="password"
          autoComplete="current-password"
          disabled={busy}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              login();
            }
          }}
        />

        {error && <div className="auth-error">{error}</div>}

        <button
          className="primary"
          onClick={login}
          disabled={busy}
        >
          {busy ? "Signing in..." : "Sign In"}
        </button>

        <small>
          Your personal portfolio is protected by secure authentication.
        </small>
      </div>
    </div>
  );
}
