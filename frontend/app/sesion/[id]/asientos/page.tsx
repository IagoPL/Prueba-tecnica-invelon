// app/pelicula/[id]/sesiones/page.tsx
import { Sesiones } from "@/components/sesiones"

type Params = { id: string }
type Props = { params: Promise<Params> }

export default async function SesionesPage({ params }: Props) {
  const { id } = await params
  return <Sesiones peliculaId={id} />
}
