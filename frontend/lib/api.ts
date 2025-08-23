// lib/api.ts
import axios, { AxiosError } from "axios"

// --------- Base URL (sin auth) ---------
const baseURL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1"
console.log("[api] Base URL:", baseURL)

export const api = axios.create({ baseURL })

// --------- Interceptors (solo log) ---------
api.interceptors.request.use(
  (config) => {
    const method = (config.method || "get").toUpperCase()
    console.log("[api] →", method, (config.baseURL || "") + (config.url || ""))
    return config
  },
  (error) => Promise.reject(error)
)

api.interceptors.response.use(
  (response) => {
    console.log("[api] ←", response.status, response.config.url)
    return response
  },
  (error: AxiosError) => {
    console.error("[api] ✖", error.response?.status, error.config?.url, error.response?.data || "")
    return Promise.reject(error)
  }
)

// --------- Tipos ---------
export interface Pelicula {
  id: number
  titulo: string
  poster_url?: string
  clasificacion?: string
  descripcion?: string
  duracion_min?: number
  clasificacion_display?: string
}

export interface Sesion {
  id: number
  pelicula: {
    id: number
    titulo: string
    descripcion: string
    duracion_min: number
    clasificacion: string
    clasificacion_display: string
    poster_url: string
  }
  inicio: string // ISO
  sala: string
  filas: number
  columnas: number
  asientos_totales: number
  asientos_disponibles: number
  reservadas?: number
  pagadas?: number
}

export interface Asiento {
  fila: string
  numero: number
  estado: "libre" | "reservada" | "pagada"
}

export interface Entrada {
  id: number
  sesion: number
  fila: string
  numero: number
  email: string
  estado: "reservada" | "pagada"
  etiqueta_asiento?: string
  creada_en?: string
}

type Paginated<T> = { count: number; next: string | null; previous: string | null; results: T[] }

function unwrap<T>(data: any): T[] {
  if (!data) return []
  if (Array.isArray(data)) return data as T[]
  if (Array.isArray((data as Paginated<T>).results)) return (data as Paginated<T>).results
  return []
}

// --------- Películas ---------
export async function getPeliculas(params?: { search?: string; ordering?: string; page?: number }) {
  try {
    const { data } = await api.get<Paginated<Pelicula> | Pelicula[]>("/peliculas/", { params })
    return unwrap<Pelicula>(data)
  } catch {
    return []
  }
}

export async function getPelicula(id: number) {
  const { data } = await api.get<Pelicula>(`/peliculas/${id}/`)
  return data
}

// --------- Sesiones ---------
export async function getSesiones(params?: {
  pelicula?: number
  pelicula_id?: number // compat: lo mapeamos a 'pelicula'
  sala?: string
  inicio_after?: string
  inicio_before?: string
  search?: string
  ordering?: string
  page?: number
}) {
  try {
    const mapped = { ...(params || {}) } as any
    if (mapped.pelicula_id && !mapped.pelicula) mapped.pelicula = mapped.pelicula_id
    delete mapped.pelicula_id
    const { data } = await api.get<Paginated<Sesion> | Sesion[]>("/sesiones/", { params: mapped })
    return unwrap<Sesion>(data)
  } catch {
    return []
  }
}

export async function getSesion(id: number) {
  const { data } = await api.get<Sesion>(`/sesiones/${id}/`)
  return data
}

export async function getAsientos(sesionId: number, includeEstado = true) {
  try {
    const params = includeEstado ? { include: "estado" } : {}
    const { data } = await api.get(`/sesiones/${sesionId}/asientos/`, { params })
    const layout = data?.layout || []
    const asientos: Asiento[] = []
    for (const fila of layout) {
      if (Array.isArray(fila)) asientos.push(...fila)
    }
    return asientos
  } catch {
    return []
  }
}

// --------- Entradas (guest checkout) ---------
export async function crearEntrada(payload: {
  sesion: number
  fila: string
  numero: number
  email: string
  estado: "reservada"
}) {
  try {
    const { data } = await api.post<Entrada>("/entradas/", payload)
    return data
  } catch (error: any) {
    const status = error?.response?.status
    if (status === 400 || status === 409) {
      throw new Error("Ese asiento ya no está disponible")
    }
    throw new Error("Error al crear la reserva")
  }
}

export async function pagarEntrada(id: number) {
  try {
    const { data } = await api.post<Entrada>(`/entradas/${id}/pagar/`)
    return data
  } catch {
    throw new Error("Error al procesar el pago")
  }
}
