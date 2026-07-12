let accessToken: string | undefined;
let refreshSession: (() => Promise<string | undefined>) | undefined;

export function setSessionBridge(token: string | undefined, refresh?: () => Promise<string | undefined>) {
  accessToken = token;
  refreshSession = refresh;
}

export function getAccessToken() { return accessToken; }
export async function refreshAccessToken() { return refreshSession?.(); }
