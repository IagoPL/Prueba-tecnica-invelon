"use client"

import { createContext, useContext, useReducer, type ReactNode } from "react"

interface Pelicula {
  id: number
  titulo: string
  poster?: string
  clasificacion?: string
}

interface Sesion {
  id: number
  pelicula_id: number
  fecha: string
  hora: string
  sala: string
  disponibles: number
  total: number
}

interface Asiento {
  fila: string
  numero: number
  estado: "libre" | "reservada" | "pagada"
}

interface Entrada {
  id: number
  sesion: number
  fila: string
  numero: number
  email: string
  estado: "reservada" | "pagada"
  pelicula?: string
  hora?: string
  sala?: string
  etiqueta_asiento?: string
}

interface CinemaState {
  pelicula: Pelicula | null
  sesion: Sesion | null
  asientosSeleccionados: Asiento[]
  entradasCreadas: Entrada[]
}

type CinemaAction =
  | { type: "SET_PELICULA"; payload: Pelicula }
  | { type: "SET_SESION"; payload: Sesion }
  | { type: "TOGGLE_ASIENTO"; payload: Asiento }
  | { type: "CLEAR_ASIENTOS" }
  | { type: "SET_ENTRADAS_CREADAS"; payload: Entrada[] }
  | { type: "RESET" }

const initialState: CinemaState = {
  pelicula: null,
  sesion: null,
  asientosSeleccionados: [],
  entradasCreadas: [],
}

function cinemaReducer(state: CinemaState, action: CinemaAction): CinemaState {
  switch (action.type) {
    case "SET_PELICULA":
      return { ...state, pelicula: action.payload }
    case "SET_SESION":
      return { ...state, sesion: action.payload }
    case "TOGGLE_ASIENTO":
      const exists = state.asientosSeleccionados.find(
        (a) => a.fila === action.payload.fila && a.numero === action.payload.numero,
      )
      if (exists) {
        return {
          ...state,
          asientosSeleccionados: state.asientosSeleccionados.filter(
            (a) => !(a.fila === action.payload.fila && a.numero === action.payload.numero),
          ),
        }
      } else {
        return {
          ...state,
          asientosSeleccionados: [...state.asientosSeleccionados, action.payload],
        }
      }
    case "CLEAR_ASIENTOS":
      return { ...state, asientosSeleccionados: [] }
    case "SET_ENTRADAS_CREADAS":
      return { ...state, entradasCreadas: action.payload }
    case "RESET":
      return initialState
    default:
      return state
  }
}

interface CinemaContextType {
  state: CinemaState
  setPelicula: (pelicula: Pelicula) => void
  setSesion: (sesion: Sesion) => void
  toggleAsiento: (asiento: Asiento) => void
  clearAsientos: () => void
  setEntradasCreadas: (entradas: Entrada[]) => void
  reset: () => void
}

const CinemaContext = createContext<CinemaContextType | undefined>(undefined)

export function CinemaProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(cinemaReducer, initialState)

  const setPelicula = (pelicula: Pelicula) => {
    dispatch({ type: "SET_PELICULA", payload: pelicula })
  }

  const setSesion = (sesion: Sesion) => {
    dispatch({ type: "SET_SESION", payload: sesion })
  }

  const toggleAsiento = (asiento: Asiento) => {
    dispatch({ type: "TOGGLE_ASIENTO", payload: asiento })
  }

  const clearAsientos = () => {
    dispatch({ type: "CLEAR_ASIENTOS" })
  }

  const setEntradasCreadas = (entradas: Entrada[]) => {
    dispatch({ type: "SET_ENTRADAS_CREADAS", payload: entradas })
  }

  const reset = () => {
    dispatch({ type: "RESET" })
  }

  return (
    <CinemaContext.Provider
      value={{
        state,
        setPelicula,
        setSesion,
        toggleAsiento,
        clearAsientos,
        setEntradasCreadas,
        reset,
      }}
    >
      {children}
    </CinemaContext.Provider>
  )
}

export function useCinema() {
  const context = useContext(CinemaContext)
  if (context === undefined) {
    throw new Error("useCinema must be used within a CinemaProvider")
  }
  return context
}
