"use client"

import type React from "react"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Skeleton } from "@/components/ui/skeleton"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { getAsientos, crearEntrada, type Asiento } from "@/lib/api"
import { useCinema } from "@/context/cinema-context"
import { cn } from "@/lib/utils"

interface Props {
  sesionId: string
}

export function Asientos({ sesionId }: Props) {
  const [asientos, setAsientos] = useState<Asiento[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [email, setEmail] = useState("")
  const [creandoEntradas, setCreandoEntradas] = useState(false)
  const router = useRouter()
  const { state, toggleAsiento, clearAsientos, setEntradasCreadas } = useCinema()

  useEffect(() => {
    cargarAsientos()
  }, [sesionId])

  const cargarAsientos = async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await getAsientos(Number.parseInt(sesionId), true)
      setAsientos(data)
    } catch (err) {
      setError("Error al cargar los asientos")
    } finally {
      setLoading(false)
    }
  }

  const handleAsientoClick = (asiento: Asiento) => {
    if (asiento.estado === "libre") {
      toggleAsiento(asiento)
    }
  }

  const isAsientoSeleccionado = (asiento: Asiento) => {
    return state.asientosSeleccionados.some((a) => a.fila === asiento.fila && a.numero === asiento.numero)
  }

  const handleConfirmarSeleccion = async (e: React.FormEvent) => {
    e.preventDefault()

    if (state.asientosSeleccionados.length === 0) {
      setError("Debe seleccionar al menos un asiento")
      return
    }

    if (!email.trim()) {
      setError("El email es requerido")
      return
    }

    try {
      setCreandoEntradas(true)
      setError(null)

      const entradas = []
      let hasSimulatedEntries = false

      for (const asiento of state.asientosSeleccionados) {
        try {
          const entrada = await crearEntrada({
            sesion: Number.parseInt(sesionId),
            fila: asiento.fila,
            numero: asiento.numero,
            email: email.trim(),
            estado: "reservada",
          })

          if (entrada.simulated) {
            hasSimulatedEntries = true
          }

          entradas.push(entrada)
        } catch (err: any) {
          setError(err.message || "Error al crear la entrada")
          await cargarAsientos()
          return
        }
      }

      setEntradasCreadas(
        entradas.map((entrada) => ({
          ...entrada,
          isDemo: hasSimulatedEntries,
        })),
      )
      clearAsientos()
      router.push("/confirmacion")
    } catch (err: any) {
      setError(err.message || "Error al crear las entradas")
    } finally {
      setCreandoEntradas(false)
    }
  }

  const asientosPorFila = asientos.reduce(
    (acc, asiento) => {
      if (!acc[asiento.fila]) {
        acc[asiento.fila] = []
      }
      acc[asiento.fila].push(asiento)
      return acc
    },
    {} as Record<string, Asiento[]>,
  )

  const filasOrdenadas = Object.keys(asientosPorFila).sort()
  filasOrdenadas.forEach((fila) => {
    asientosPorFila[fila].sort((a, b) => a.numero - b.numero)
  })

  if (loading) {
    return (
      <div className="container mx-auto p-4">
        <h1 className="text-3xl font-bold mb-6">Cargando...</h1>
        <Skeleton className="h-64 w-full" />
      </div>
    )
  }

  if (error && asientos.length === 0) {
    return (
      <div className="container mx-auto p-4">
        <Alert className="mb-6">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
        <Button onClick={() => cargarAsientos()}>Reintentar</Button>
      </div>
    )
  }

  return (
    <div className="container mx-auto p-4">
      <div className="mb-6">
        <Button variant="outline" onClick={() => router.back()} className="mb-4">
          ← Volver a sesiones
        </Button>
        <h1 className="text-3xl font-bold">Seleccionar asientos</h1>
        {state.sesion && (
          <p className="text-muted-foreground">
            {state.pelicula?.titulo} - Sala {state.sesion.sala}
          </p>
        )}
      </div>

      {error && (
        <Alert className="mb-6">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <div className="grid lg:grid-cols-2 gap-8">
        <div>
          <Card>
            <CardHeader>
              <CardTitle>Mapa de asientos</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="mb-4 text-center">
                <div className="bg-muted h-2 w-full rounded mb-2"></div>
                <p className="text-sm text-muted-foreground">PANTALLA</p>
              </div>

              <div className="space-y-2">
                {filasOrdenadas.map((fila) => (
                  <div key={fila} className="flex items-center gap-2">
                    <span className="w-8 text-center font-mono text-sm">{fila}</span>
                    <div className="flex gap-1">
                      {asientosPorFila[fila].map((asiento) => (
                        <button
                          key={`${asiento.fila}-${asiento.numero}`}
                          onClick={() => handleAsientoClick(asiento)}
                          disabled={asiento.estado !== "libre"}
                          className={cn("w-8 h-8 text-xs rounded border-2 transition-colors", {
                            "bg-green-100 border-green-300 hover:bg-green-200":
                              asiento.estado === "libre" && !isAsientoSeleccionado(asiento),
                            "bg-blue-500 border-blue-600 text-white": isAsientoSeleccionado(asiento),
                            "bg-red-100 border-red-300 cursor-not-allowed": asiento.estado === "reservada",
                            "bg-gray-400 border-gray-500 cursor-not-allowed text-white": asiento.estado === "pagada",
                          })}
                        >
                          {asiento.numero}
                        </button>
                      ))}
                    </div>
                  </div>
                ))}
              </div>

              <div className="mt-6 flex gap-4 text-sm">
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 bg-green-100 border-2 border-green-300 rounded"></div>
                  <span>Libre</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 bg-blue-500 border-2 border-blue-600 rounded"></div>
                  <span>Seleccionado</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 bg-red-100 border-2 border-red-300 rounded"></div>
                  <span>Reservado</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 bg-gray-400 border-2 border-gray-500 rounded"></div>
                  <span>Pagado</span>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        <div>
          <Card>
            <CardHeader>
              <CardTitle>Resumen de selección</CardTitle>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleConfirmarSeleccion} className="space-y-4">
                <div>
                  <Label htmlFor="email">Email *</Label>
                  <Input
                    id="email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="tu@email.com"
                    required
                  />
                </div>

                <div>
                  <h4 className="font-medium mb-2">Asientos seleccionados:</h4>
                  {state.asientosSeleccionados.length === 0 ? (
                    <p className="text-muted-foreground text-sm">No hay asientos seleccionados</p>
                  ) : (
                    <div className="space-y-1">
                      {state.asientosSeleccionados.map((asiento) => (
                        <div key={`${asiento.fila}-${asiento.numero}`} className="text-sm">
                          Fila {asiento.fila}, Asiento {asiento.numero}
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                <Button
                  type="submit"
                  className="w-full"
                  disabled={state.asientosSeleccionados.length === 0 || creandoEntradas}
                >
                  {creandoEntradas ? "Procesando..." : "Confirmar selección"}
                </Button>
              </form>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
