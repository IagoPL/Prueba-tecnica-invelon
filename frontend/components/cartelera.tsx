"use client"

import type React from "react"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Skeleton } from "@/components/ui/skeleton"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { getPeliculas, type Pelicula } from "@/lib/api"
import { useCinema } from "@/context/cinema-context"

export function Cartelera() {
  const [peliculas, setPeliculas] = useState<Pelicula[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [busqueda, setBusqueda] = useState("")
  const router = useRouter()
  const { setPelicula } = useCinema()

  useEffect(() => {
    cargarPeliculas()
  }, [])

  const cargarPeliculas = async (search?: string) => {
    try {
      console.log("[v0] Starting to load movies...")
      setLoading(true)
      setError(null)
      const data = await getPeliculas(search ? { search } : undefined)
      console.log("[v0] Movies loaded:", data)
      setPeliculas(Array.isArray(data) ? data : [])

      if (!data || data.length === 0) {
        console.log("[v0] No movies returned from API")
      }
    } catch (err) {
      console.error("[v0] Error loading movies:", err)
      setError("Error al cargar las películas. Verifique que la API esté disponible en la URL configurada.")
      setPeliculas([])
    } finally {
      setLoading(false)
    }
  }

  const handleBuscar = (e: React.FormEvent) => {
    e.preventDefault()
    cargarPeliculas(busqueda)
  }

  const handleVerSesiones = (pelicula: Pelicula) => {
    setPelicula(pelicula)
    router.push(`/pelicula/${pelicula.id}/sesiones`)
  }

  const handleImageError = (e: React.SyntheticEvent<HTMLImageElement>) => {
    const target = e.target as HTMLImageElement
    // Only change src if it's not already the fallback image
    if (!target.src.includes("abstract-movie-poster.png")) {
      target.src = "/abstract-movie-poster.png"
    }
  }

  if (loading) {
    return (
      <div className="container mx-auto p-4">
        <h1 className="text-3xl font-bold mb-6">Cartelera</h1>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {Array.from({ length: 6 }).map((_, i) => (
            <Card key={i}>
              <CardHeader>
                <Skeleton className="h-4 w-3/4" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-48 w-full mb-4" />
                <Skeleton className="h-4 w-1/2" />
              </CardContent>
              <CardFooter>
                <Skeleton className="h-10 w-full" />
              </CardFooter>
            </Card>
          ))}
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="container mx-auto p-4">
        <Alert className="mb-6">
          <AlertDescription>
            {error}
            <br />
            <small className="text-muted-foreground">
              URL de API: {process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000/api/v1"}
            </small>
          </AlertDescription>
        </Alert>
        <Button onClick={() => cargarPeliculas()}>Reintentar</Button>
      </div>
    )
  }

  return (
    <div className="container mx-auto p-4">
      <h1 className="text-3xl font-bold mb-6">Cartelera</h1>

      <form onSubmit={handleBuscar} className="mb-6">
        <div className="flex gap-2">
          <Input
            type="text"
            placeholder="Buscar película por título..."
            value={busqueda}
            onChange={(e) => setBusqueda(e.target.value)}
            className="flex-1"
          />
          <Button type="submit">Buscar</Button>
        </div>
      </form>

      {peliculas.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-muted-foreground">No hay resultados</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {peliculas.map((pelicula) => (
            <Card key={pelicula.id}>
              <CardHeader>
                <CardTitle>{pelicula.titulo}</CardTitle>
              </CardHeader>
              <CardContent>
                <img
                  src={
                    pelicula.poster_url && !pelicula.poster_url.includes("example.com")
                      ? pelicula.poster_url
                      : "/abstract-movie-poster.png"
                  }
                  alt={pelicula.titulo}
                  className="w-full h-48 object-cover rounded mb-4"
                  onError={handleImageError}
                />
                <div className="space-y-2">
                  {pelicula.descripcion && (
                    <p className="text-sm text-muted-foreground line-clamp-3">{pelicula.descripcion}</p>
                  )}
                  {pelicula.duracion_min && (
                    <p className="text-sm text-muted-foreground">Duración: {pelicula.duracion_min} min</p>
                  )}
                  {pelicula.clasificacion_display && (
                    <p className="text-sm text-muted-foreground">Clasificación: {pelicula.clasificacion_display}</p>
                  )}
                </div>
              </CardContent>
              <CardFooter>
                <Button onClick={() => handleVerSesiones(pelicula)} className="w-full">
                  Ver sesiones
                </Button>
              </CardFooter>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
