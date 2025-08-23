// lib/auth.ts
import axios from "axios"

const baseURL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1"

// Claves de storage (mismo naming que en lib/api.ts)
const ACCESS_KEY = "auth_access"
const REFRESH_KEY = "auth_refresh"

export function getAccess(): string | null {
  if (typeof window === "undefined") return null
  return localStorage.getItem(ACCESS_KEY)
}
export function getRefresh(): string | null {
  if (typeof window === "undefined") return null
  return localStorage.getItem(REFRESH_KEY)
}
export function setTokens(tokens: { access: string; refresh?: string }) {
  if (typeof window === "undefined") return
  localStorage.setItem(ACCESS_KEY, tokens.access)
  if (tokens.refresh) localStorage.setItem(REFRESH_KEY, tokens.refresh)
}
export function clearTokens() {
  if (typeof window === "undefined") return
  localStorage.removeItem(ACCESS_KEY)
  localStorage.removeItem(REFRESH_KEY)
}

export async function login(username: string, password: string) {
  const { data } = await axios.post<{ access: string; refresh: string }>(
    `${baseURL}/token/`,
    { username, password }
  )
  setTokens(data)
  return data
}

export async function refreshToken(): Promise<string> {
  const refresh = getRefresh()
  if (!refresh) throw new Error("No refresh token")
  const { data } = await axios.post<{ access: string }>(
    `${baseURL}/token/refresh/`,
    { refresh }
  )
  setTokens({ access: data.access })
  return data.access
}
