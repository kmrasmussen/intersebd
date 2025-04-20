"use client"

import { Button } from "@/components/ui/button"
import { ResponseCard } from "@/components/response-card"

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

type AlternativesSectionProps = {
  alternatives: Response[]
  showAlternatives: boolean
  setShowAlternatives: (show: boolean) => void
}

export function AlternativesSection({ alternatives, showAlternatives, setShowAlternatives }: AlternativesSectionProps) {
  return (
    <>
      <div className="flex items-center justify-between mb-2">
        <h3 className="font-medium">Alternatives:</h3>
        <Button variant="outline" size="sm" onClick={() => setShowAlternatives(!showAlternatives)}>
          {showAlternatives ? "Hide Alternatives" : "Show/Refresh Alternatives"}
        </Button>
      </div>

      {showAlternatives && alternatives.length > 0 && (
        <div className="space-y-4">
          {alternatives.map((response, index) => (
            <ResponseCard key={index} response={response} isAlternative />
          ))}
        </div>
      )}

      {showAlternatives && alternatives.length === 0 && (
        <div className="p-4 bg-gray-50 rounded-md text-gray-500 italic text-center">
          No alternative responses available.
        </div>
      )}
    </>
  )
}
