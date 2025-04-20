import { ResponseCard } from "@/components/response-card"; // Corrected path

type Response = {
  id: string
  content: string
  model: string
  created: string
  annotations: Array<{
    reward: number
    by: string
    at: string
  }>
  metadata?: Record<string, any>
  is_json: boolean
  obeys_schema: boolean | null
}

export function ResponseSection({ response }: { response: Response }) {
  return <ResponseCard response={response} />
}
