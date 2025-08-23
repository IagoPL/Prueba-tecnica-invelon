"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { registerUser, login } from "@/lib/api"

export default function RegisterPage() {
  const [username, setUsername] = useState("")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const router = useRouter()

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      await registerUser({ username, email, password })
      await login(username, password) // login automático
      router.push("/")
    } catch (err: any) {
      setError(err?.message || "No se pudo registrar")
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="min-h-dvh grid place-items-center p-6">
      <form onSubmit={onSubmit} className="w-full max-w-sm space-y-4 border rounded-xl p-6 shadow-sm">
        <h1 className="text-xl font-semibold">Crear cuenta</h1>

        <div className="space-y-2">
          <label className="block text-sm">Usuario</label>
          <input
            className="w-full border rounded px-3 py-2"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="usuario"
            required
          />
        </div>

        <div className="space-y-2">
          <label className="block text-sm">Email</label>
          <input
            className="w-full border rounded px-3 py-2"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="correo@ejemplo.com"
            required
          />
        </div>

        <div className="space-y-2">
          <label className="block text-sm">Contraseña</label>
          <input
            className="w-full border rounded px-3 py-2"
            type="password"
            autoComplete="new-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
            required
            minLength={6}
          />
        </div>

        {error && <p className="text-red-600 text-sm">{error}</p>}

        <button
          type="submit"
          disabled={loading}
          className="w-full bg-black text-white rounded px-4 py-2 disabled:opacity-60"
        >
          {loading ? "Creando…" : "Crear cuenta"}
        </button>

        <p className="text-sm text-center">
          ¿Ya tienes cuenta? <a href="/login" className="underline">Inicia sesión</a>
        </p>
      </form>
    </main>
  )
}
