"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { login, isLoggedIn } from "@/lib/api"

export default function LoginPage() {
  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const router = useRouter()

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      await login(username, password) // guarda access+refresh en localStorage
      router.push("/")                // vuelve a la home
    } catch (err) {
      setError("Credenciales inválidas")
    } finally {
      setLoading(false)
    }
  }

  // Si ya está logueado, redirige (evita ver el login)
  if (typeof window !== "undefined" && isLoggedIn()) {
    router.replace("/")
  }

  return (
    <main className="min-h-dvh grid place-items-center p-6">
      <form onSubmit={onSubmit} className="w-full max-w-sm space-y-4 border rounded-xl p-6 shadow-sm">
        <h1 className="text-xl font-semibold">Iniciar sesión</h1>

        <div className="space-y-2">
          <label className="block text-sm">Usuario</label>
          <input
            className="w-full border rounded px-3 py-2"
            autoComplete="username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="usuario"
            required
          />
        </div>

        <div className="space-y-2">
          <label className="block text-sm">Contraseña</label>
          <input
            className="w-full border rounded px-3 py-2"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
            required
          />
        </div>

        {error && <p className="text-red-600 text-sm">{error}</p>}

        <button
          type="submit"
          disabled={loading}
          className="w-full bg-black text-white rounded px-4 py-2 disabled:opacity-60"
        >
          {loading ? "Entrando…" : "Entrar"}
        </button>

        <p className="text-sm text-center">
          ¿No tienes cuenta? <a href="/register" className="underline">Registrarse</a>
        </p>
      </form>
    </main>
  )
}
