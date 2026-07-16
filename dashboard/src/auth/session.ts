const TOKEN_KEY = 'har_access_token';

let cachedToken: string | undefined;

export function setSessionBridge(token: string | undefined) {
  cachedToken = token;
  if (token) {
    localStorage.setItem(TOKEN_KEY, token);
  } else {
    localStorage.removeItem(TOKEN_KEY);
  }
}

export function getAccessToken(): string | undefined {
  if (cachedToken) return cachedToken;
  const stored = localStorage.getItem(TOKEN_KEY);
  if (stored) { cachedToken = stored; return stored; }
  return undefined;
}

export function clearSession() {
  cachedToken = undefined;
  localStorage.removeItem(TOKEN_KEY);
}

// No refresh needed — user re-logs in when token expires.
export async function refreshAccessToken(): Promise<string | undefined> {
  return undefined;
}
