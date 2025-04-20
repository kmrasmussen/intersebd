"use client"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"
import { RefreshCw } from "lucide-react"

interface AnnotationProgressBarProps {
  title: string
  annotatedResponses: number
  requiredResponses: number
  onRefresh?: () => void
  isRefreshing?: boolean
}

export function AnnotationProgressBar({
  title,
  annotatedResponses,
  requiredResponses,
  onRefresh,
  isRefreshing = false,
}: AnnotationProgressBarProps) {
  const progressPercentage = Math.min(100, Math.round((annotatedResponses / requiredResponses) * 100))
  const isReady = annotatedResponses >= requiredResponses

  return (
    <div className="p-3 bg-gray-50 rounded-md">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <p className="font-medium">{title}</p>
          {onRefresh && (
            <Button
              variant="ghost"
              size="sm"
              className={`h-6 w-6 p-0 ${isRefreshing ? "animate-spin" : ""}`}
              onClick={onRefresh}
              disabled={isRefreshing}
              aria-label={`Refresh ${title.toLowerCase()}`}
            >
              <RefreshCw className="h-3.5 w-3.5" />
            </Button>
          )}
        </div>
        <Badge variant="outline" className={isReady ? "bg-green-50 text-green-600" : "bg-amber-50 text-amber-600"}>
          {annotatedResponses}/{requiredResponses} Responses
        </Badge>
      </div>
      <Progress value={progressPercentage} className="h-2" />
      <p className="text-sm text-gray-500 mt-2">
        {isReady
          ? "You have enough annotated responses to generate a dataset."
          : `You need ${requiredResponses - annotatedResponses} more annotated responses to generate a dataset.`}
      </p>
    </div>
  )
}
