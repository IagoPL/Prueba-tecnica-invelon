"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { pagarEntrada } from "@/lib/api"
import { useCinema } from "@/context/cinema-context"

export function Confirmacion() {
  const [pagandoEntradas, setPagandoEntradas] = useState<Set<number>>(new Set())
  const [error, setError] = useState<string | null>(null)
  const router = useRouter()
  const { state, setEntradasCreadas, reset } = useCinema()

  const hasSimulatedEntries = state.entradasCreadas.some((entrada: any) => entrada.isDemo)

  const handlePagar = async (entradaId: number) => {
    try {
      setPagandoEntradas((prev) => new Set(prev).add(entradaId))
      setError(null)

      const entradaPagada = await pagarEntrada(entradaId)

      // Actualizar el estado de la entrada
      const entradasActualizadas = state.entradasCreadas.map((entrada) =>
        entrada.id === entradaId ? { ...entrada, estado: "pagada" as const } : entrada,
      )
      setEntradasCreadas(entradasActualizadas)
    } catch (err) {
      setError("Error al procesar el pago")
    } finally {
      setPagandoEntradas((prev) => {
        const newSet = new Set(prev)
        newSet.delete(entradaId)
        return newSet
      })
    }
  }

  const handleNuevaCompra = () => {
    reset()
    router.push("/")
  }

  if (state.entradasCreadas.length === 0) {
    return (
      <div className="container mx-auto p-4">
        <div className="text-center py-12">
          <h1 className="text-3xl font-bold mb-4">No hay entradas</h1>
          <p className="text-muted-foreground mb-6">No tienes entradas pendientes de confirmación</p>
          <Button onClick={() => router.push("/")}>Ir a cartelera</Button>
        </div>
      </div>
    )
  }

  const formatearFechaHora = (fecha?: string, hora?: string) => {
    if (!fecha || !hora) return "Fecha no disponible"
    const fechaObj = new Date(`${fecha}T${hora}`)
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

  return (
    <div className="container mx-auto p-4">
      <div className="mb-6">
        <h1 className="text-3xl font-bold">Confirmación de entradas</h1>
        <p className="text-muted-foreground">Revisa tus entradas y procede con el pago</p>
      </div>

      {hasSimulatedEntries && (
        <Alert className="mb-6 border-blue-200 bg-blue-50">
          <AlertDescription className="text-blue-800">
            <strong>Modo Demo:</strong> Esta es una simulación para propósitos de demostración. Las reservas no son
            reales ya que la API requiere autenticación.
          </AlertDescription>
        </Alert>
      )}

      {error && (
        <Alert className="mb-6">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <div className="space-y-4 mb-6">
        {state.entradasCreadas.map((entrada) => (
          <Card key={entrada.id}>
            <CardHeader>
              <CardTitle className="flex justify-between items-center">
                <span>{entrada.pelicula || state.pelicula?.titulo || "Película"}</span>
                <span
                  className={`text-sm px-2 py-1 rounded ${
                    entrada.estado === "pagada" ? "bg-green-100 text-green-800" : "bg-yellow-100 text-yellow-800"
                  }`}
                >
                  {entrada.estado === "pagada" ? "Pagada" : "Reservada"}
                </span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid md:grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-muted-foreground">Fecha y hora:</p>
                  <p className="font-medium">{formatearFechaHora(entrada.hora, state.sesion?.hora)}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Sala:</p>
                  <p className="font-medium">{entrada.sala || state.sesion?.sala || "No disponible"}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Asiento:</p>
                  <p className="font-medium">
                    {entrada.etiqueta_asiento || `Fila ${entrada.fila}, Asiento ${entrada.numero}`}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Email:</p>
                  <p className="font-medium">{entrada.email}</p>
                </div>
              </div>

              {entrada.estado === "reservada" && (
                <div className="mt-4">
                  <Button
                    onClick={() => handlePagar(entrada.id)}
                    disabled={pagandoEntradas.has(entrada.id)}
                    className="w-full md:w-auto"
                  >
                    {pagandoEntradas.has(entrada.id) ? "Procesando pago..." : "Pagar"}
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="flex gap-4">
        <Button onClick={handleNuevaCompra} variant="outline">
          Nueva compra
        </Button>
        <Button onClick={() => router.push("/")}>Volver a cartelera</Button>
      </div>
    </div>
  )
}
