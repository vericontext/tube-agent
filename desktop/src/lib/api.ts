import { invoke } from "@tauri-apps/api/core";

let _baseUrl: string | null = null;

export async function getApiBase(): Promise<string> {
  if (_baseUrl) return _baseUrl;
  const port = await invoke<number>("get_sidecar_port");
  _baseUrl = `http://127.0.0.1:${port}/api/v1`;
  return _baseUrl;
}

export async function pingHealth(): Promise<boolean> {
  const base = await getApiBase();
  const url = base.replace(/\/api\/v1$/, "/health");
  try {
    const res = await fetch(url);
    return res.ok;
  } catch {
    return false;
  }
}

export async function waitForReady(maxAttempts = 30, intervalMs = 500): Promise<boolean> {
  for (let i = 0; i < maxAttempts; i++) {
    if (await pingHealth()) return true;
    await new Promise((r) => setTimeout(r, intervalMs));
  }
  return false;
}
