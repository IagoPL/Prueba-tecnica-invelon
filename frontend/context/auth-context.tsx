"use client"

import { createContext, useContext, useEffect, useMemo, useState } from "react"
import { login as apiLogin, logout as apiLogout, registerUser } from "@/lib/api"

type AuthCtx = {
  isAuthenticated: boolean
  loading: boolean
  login: (u: string, p: string) => Promise<void>
  register: (u: string, e: string, p: string) => Promise<void>
  logout: () => void
}

const Ctx = createContext<AuthCtx | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [loading, setLoading] = useState(true)
  const [isAuthenticated, setAuth] = useState(false)

  useEffect(() => {
    try {
      const has = typeof window !== "undefined" && !!localStorage.getItem("auth_access")
      setAuth(has)
    } finally {
      setLoading(false)
    }
  }, [])

  const value = useMemo<AuthCtx>(() => ({
    isAuthenticated,
    loading,
    login: async (username, password) => {
      await apiLogin(username, password)
      setAuth(true)
    },
    register: async (username, email, password) => {
      await registerUser({ username, email, password })
      // tras registrar, haz login automático si quieres:
      await apiLogin(username, password)
      setAuth(true)
    },
    logout: () => {
      apiLogout()
      setAuth(false)
    },
  }), [isAuthenticated, loading])

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

export function useAuth() {
  const ctx = useContext(Ctx)
  if (!ctx) throw new Error("useAuth must be used within <AuthProvider>")
  return ctx
}
