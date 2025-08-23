"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { getSesiones, type Sesion } from "@/lib/api"
import { useCinema } from "@/context/cinema-context"

interface Props {
  peliculaId: string
}

export function Sesiones({ peliculaId }: Props) {
  const [sesiones, setSesiones] = useState<Sesion[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const router = useRouter()
  const { state, setSesion } = useCinema()

  useEffect(() => {
    cargarSesiones()
  }, [peliculaId])

  const cargarSesiones = async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await getSesiones({ pelicula_id: Number.parseInt(peliculaId) })
      setSesiones(data)
    } catch (err) {
      setError("Error al cargar las sesiones")
    } finally {
      setLoading(false)
    }
  }

  const handleElegirAsientos = (sesion: Sesion) => {
    setSesion(sesion)
    router.push(`/sesion/${sesion.id}/asientos`)
  }

  const formatearFechaHora = (inicioISO: string) => {
    const fechaObj = new Date(inicioISO)
    if (isNaN(fechaObj.getTime())) {
      return "Fecha no disponible"
    }
    return fechaObj.toLocaleString("es-ES", {
      weekday: "long",
      year: "numeric",
      month: "long",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    })
  }

  if (loading) {
    return (
      <div className="container mx-auto p-4">
        <h1 className="text-3xl font-bold mb-6">Cargando...</h1>
        <div className="space-y-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Card key={i}>
              <CardHeader>
                <Skeleton className="h-6 w-3/4" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-4 w-1/2 mb-2" />
                <Skeleton className="h-4 w-1/3" />
              </CardContent>
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
          <AlertDescription>{error}</AlertDescription>
        </Alert>
        <Button onClick={() => cargarSesiones()}>Reintentar</Button>
      </div>
    )
  }

  return (
    <div className="container mx-auto p-4">
      <div className="mb-6">
        <Button variant="outline" onClick={() => router.push("/")} className="mb-4">
          ← Volver a cartelera
        </Button>
        <h1 className="text-3xl font-bold">Sesiones {state.pelicula ? `- ${state.pelicula.titulo}` : ""}</h1>
      </div>

      {sesiones.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-muted-foreground">No hay sesiones disponibles</p>
        </div>
      ) : (
        <div className="space-y-4">
          {sesiones.map((sesion) => (
            <Card key={sesion.id}>
              <CardHeader>
                <CardTitle>{formatearFechaHora(sesion.inicio)}</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex justify-between items-center">
                  <div>
                    <p className="text-sm text-muted-foreground">Sala: {sesion.sala}</p>
                    <p className="text-sm text-muted-foreground">
                      Disponibles: {sesion.asientos_disponibles}/{sesion.asientos_totales}
                    </p>
                  </div>
                  <Button onClick={() => handleElegirAsientos(sesion)} disabled={sesion.asientos_disponibles === 0}>
                    {sesion.asientos_disponibles === 0 ? "Agotado" : "Elegir asientos"}
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
