// app/sesion/[id]/asientos/page.tsx
import { Asientos } from "@/components/asientos"

type Params = { id: string }
type Props = { params: Promise<Params> }

export default async function AsientosPage({ params }: Props) {
  const { id } = await params
  return <Asientos sesionId={id} />
}
