"use client"

import { useState, useMemo } from "react"
import { Card, CardContent, CardFooter, CardHeader } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Check, RefreshCw, X, ThumbsUp, ThumbsDown, Trash2, Copy, CheckCircle2 } from "lucide-react"

type Annotation = {
  id: string // <-- ADD ID FIELD
  reward: number
  by: string
  at: string
}

type ResponseMetadata = {
  completion_id?: string
  annotation_target_id?: string
  provider?: string
  model?: string
  prompt_tokens?: number
  completion_tokens?: number
  total_tokens?: number
  choice_finish_reason?: string
  choice_role?: string
  choice_content?: string
  [key: string]: any
}

type Response = {
  id: string
  annotation_target_id?: string | null
  content: string
  model: string
  created: string
  annotations: Annotation[]
  metadata?: ResponseMetadata
  is_json: boolean
  obeys_schema: boolean | null
}

// Function to format JSON with syntax highlighting
function JsonFormatter({ jsonString }: { jsonString: string }) {
  const [copied, setCopied] = useState(false)

  // Try to parse the JSON to format it properly
  const formattedJson = useMemo(() => {
    try {
      const parsed = JSON.parse(jsonString)
      return JSON.stringify(parsed, null, 2)
    } catch (e) {
      // If parsing fails, return the original string
      return jsonString
    }
  }, [jsonString])

  // Function to add syntax highlighting
  const highlightJson = (json: string) => {
    // Replace with regex to add spans with appropriate classes
    return json.replace(
      /("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+-]?\d+)?)/g,
      (match) => {
        let cls = "text-purple-600" // string
        if (/^"/.test(match) && /:$/.test(match)) {
          cls = "text-red-600" // key
        } else if (/true|false/.test(match)) {
          cls = "text-blue-600" // boolean
        } else if (/null/.test(match)) {
          cls = "text-gray-600" // null
        } else if (/^-?\d+(?:\.\d*)?(?:[eE][+-]?\d+)?$/.test(match)) {
          cls = "text-green-600" // number
        }
        return `<span class="${cls}">${match}</span>`
      },
    )
  }

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(formattedJson)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000) // Reset after 2 seconds
    } catch (err) {
      console.error("Failed to copy text: ", err)
    }
  }

  return (
    <div className="relative">
      <Button
        variant="ghost"
        size="sm"
        className="absolute top-2 right-2 h-7 w-7 p-0 bg-gray-100 hover:bg-gray-200 rounded-md z-10"
        onClick={handleCopy}
        title="Copy JSON"
      >
        {copied ? <CheckCircle2 className="h-4 w-4 text-green-500" /> : <Copy className="h-4 w-4 text-gray-500" />}
        <span className="sr-only">Copy JSON</span>
      </Button>
      <pre className="bg-gray-50 p-3 rounded-md overflow-auto text-xs font-mono">
        <code dangerouslySetInnerHTML={{ __html: highlightJson(formattedJson) }} />
      </pre>
    </div>
  )
}

export function ResponseCard({
  response,
  isAlternative = false,
  projectId,
  onAnnotationAdded,
  onResponseDeleted,
  onAnnotationDeleted, // <-- ADD new callback prop
}: {
  response: Response
  isAlternative?: boolean
  projectId: string
  onAnnotationAdded?: (targetId: string, newAnnotationData: any) => void
  onResponseDeleted?: (targetId: string) => void
  onAnnotationDeleted?: (targetId: string, annotationId: string) => void // <-- ADD prop type
}) {
  const [showRawData, setShowRawData] = useState(false)
  const [hideAnnotations, setHideAnnotations] = useState(false)
  const [isAnnotating, setIsAnnotating] = useState(false)
  const [annotationError, setAnnotationError] = useState<string | null>(null)
  const [isDeleting, setIsDeleting] = useState(false) // <-- ADD deleting state
  const [deleteError, setDeleteError] = useState<string | null>(null) // <-- ADD delete error state
  const [deletingAnnotationId, setDeletingAnnotationId] = useState<string | null>(null) // State for specific annotation deletion
  const [annotationDeleteError, setAnnotationDeleteError] = useState<string | null>(null)

  console.log(`Rendering ResponseCard ${response.id}: isDeleting=${isDeleting}, isAnnotating=${isAnnotating}`) // <-- ADD THIS

  const handleDeleteResponse = async () => {
    console.log("handleDeleteResponse called!") // <-- ADD THIS
    const targetId = response.annotation_target_id
    if (!targetId) {
      console.error("Annotation target ID is missing for deletion:", response.id)
      setDeleteError("Cannot delete: Missing target ID.")
      return
    }

    setIsDeleting(true)
    setDeleteError(null)

    const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || ""
    const GUEST_USER_ID_HEADER = "X-Guest-User-Id"
    const apiUrl = `${API_BASE_URL}/mock-next/${projectId}/annotation-targets/${targetId}`
    const guestUserId = localStorage.getItem("guestUserId")
    const headers: HeadersInit = {}
    if (guestUserId) {
      headers[GUEST_USER_ID_HEADER] = guestUserId
    }

    console.log(`Attempting to delete target ${targetId} at ${apiUrl}`)

    try {
      const apiResponse = await fetch(apiUrl, {
        method: "DELETE",
        headers: headers,
      })

      if (!apiResponse.ok && apiResponse.status !== 204) {
        let errorDetail = `HTTP error! status: ${apiResponse.status}`
        try {
          const errorData = await apiResponse.json()
          errorDetail += ` - ${errorData.detail || "Unknown error"}`
        } catch (jsonError) {
          // Ignore if response is not JSON
        }
        throw new Error(errorDetail)
      }

      console.log("Target deleted successfully:", targetId)

      if (onResponseDeleted) {
        console.log("Calling onResponseDeleted callback...")
        onResponseDeleted(targetId)
      }
    } catch (error: any) {
      console.error("Failed to delete target:", error)
      setDeleteError(error.message || "Failed to delete target")
    } finally {
      setIsDeleting(false)
    }
  }

  const handleAnnotationSubmit = async (reward: number) => {
    const targetId = response.annotation_target_id
    if (!targetId) {
      console.error("Annotation target ID is missing for this response:", response.id)
      setAnnotationError("Cannot annotate: Missing target ID.")
      return
    }

    setIsAnnotating(true)
    setAnnotationError(null)

    const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || ""
    const GUEST_USER_ID_HEADER = "X-Guest-User-Id"
    const apiUrl = `${API_BASE_URL}/mock-next/${projectId}/annotation-targets/${targetId}/annotations`
    const guestUserId = localStorage.getItem("guestUserId")
    const headers: HeadersInit = {
      "Content-Type": "application/json",
    }
    if (guestUserId) {
      headers[GUEST_USER_ID_HEADER] = guestUserId
    }

    const body = JSON.stringify({
      reward: reward,
      annotation_metadata: { submittedFrom: "ResponseCard" },
    })

    console.log(`Submitting annotation to ${apiUrl} with reward ${reward}`)

    try {
      const apiResponse = await fetch(apiUrl, {
        method: "POST",
        headers: headers,
        body: body,
      })

      if (!apiResponse.ok) {
        let errorDetail = `HTTP error! status: ${apiResponse.status}`
        try {
          const errorData = await apiResponse.json()
          errorDetail += ` - ${errorData.detail || "Unknown error"}`
        } catch (jsonError) {
          // Ignore if response is not JSON
        }
        throw new Error(errorDetail)
      }

      const newAnnotationData = await apiResponse.json()
      console.log("Annotation submitted successfully:", newAnnotationData)

      if (onAnnotationAdded) {
        console.log("Calling onAnnotationAdded callback...")
        onAnnotationAdded(targetId, newAnnotationData)
      }
    } catch (error: any) {
      console.error("Failed to submit annotation:", error)
      setAnnotationError(error.message || "Failed to submit annotation")
    } finally {
      setIsAnnotating(false)
    }
  }

  const handleDeleteAnnotation = async (annotationId: string) => {
    const targetId = response.annotation_target_id
    if (!targetId) {
      console.error("Cannot delete annotation: Missing target ID for the response.")
      setAnnotationDeleteError("Cannot delete annotation: Response target ID missing.")
      return
    }

    setDeletingAnnotationId(annotationId) // Show loading state for this specific annotation
    setAnnotationDeleteError(null)

    const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || ""
    const GUEST_USER_ID_HEADER = "X-Guest-User-Id"
    const apiUrl = `${API_BASE_URL}/mock-next/${projectId}/annotations/${annotationId}`
    const guestUserId = localStorage.getItem("guestUserId")
    const headers: HeadersInit = {}
    if (guestUserId) {
      headers[GUEST_USER_ID_HEADER] = guestUserId
    }

    console.log(`Attempting to delete annotation ${annotationId} at ${apiUrl}`)

    try {
      const apiResponse = await fetch(apiUrl, {
        method: "DELETE",
        headers: headers,
      })

      if (!apiResponse.ok && apiResponse.status !== 204) {
        let errorDetail = `HTTP error! status: ${apiResponse.status}`
        try {
          const errorData = await apiResponse.json()
          errorDetail += ` - ${errorData.detail || "Unknown error"}`
        } catch (jsonError) {
          // Ignore if response is not JSON
        }
        throw new Error(errorDetail)
      }

      console.log("Annotation deleted successfully:", annotationId)

      if (onAnnotationDeleted) {
        console.log("Calling onAnnotationDeleted callback...")
        onAnnotationDeleted(targetId, annotationId)
      }
    } catch (error: any) {
      console.error("Failed to delete annotation:", error)
      setAnnotationDeleteError(`Failed to delete annotation ${annotationId}: ${error.message || "Unknown error"}`)
    } finally {
      setDeletingAnnotationId(null) // Clear loading state
    }
  }

  return (
    <Card className="border-gray-200">
      <CardHeader className="bg-gray-50 py-3 px-4 border-b">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Badge
              variant={isAlternative ? "secondary" : "default"}
              className={isAlternative ? "bg-gray-200 text-gray-800" : ""}
            >
              {isAlternative ? "Alternative" : "Response"}
            </Badge>
            <span className="text-sm text-gray-500">{new Date(response.created).toLocaleString()}</span>
            {response.is_json && (
              <Badge variant="outline" className="bg-blue-50 text-blue-600">
                JSON
              </Badge>
            )}
            {response.obeys_schema !== null && (
              <Badge
                variant="outline"
                className={response.obeys_schema ? "bg-green-50 text-green-600" : "bg-red-50 text-red-600"}
              >
                {response.obeys_schema ? "Valid Schema" : "Invalid Schema"}
              </Badge>
            )}
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={() => setShowRawData(!showRawData)}>
              Raw
            </Button>
            <Button variant="outline" size="sm">
              <RefreshCw className="h-3.5 w-3.5" />
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="text-red-600 hover:bg-red-50"
              onClick={handleDeleteResponse}
              disabled={isDeleting || isAnnotating}
            >
              {isDeleting ? <RefreshCw className="h-3.5 w-3.5 animate-spin" /> : <Trash2 className="h-3.5 w-3.5" />}
            </Button>
          </div>
        </div>
      </CardHeader>

      <CardContent className="p-4">
        {showRawData ? (
          <div className="relative">
            <pre className="bg-gray-50 p-3 rounded-md overflow-auto text-xs font-mono">
              {JSON.stringify(response, null, 2)}
            </pre>
          </div>
        ) : response.is_json ? (
          <JsonFormatter jsonString={response.content} />
        ) : (
          <div className="mb-4">
            <p className="whitespace-pre-wrap">{response.content}</p>
          </div>
        )}
      </CardContent>

      <CardFooter className="border-t bg-gray-50 py-3 px-4 flex flex-col items-start gap-2">
        <div className="flex items-center gap-2 w-full">
          <Button
            variant="outline"
            size="sm"
            className="bg-blue-50 text-blue-600 hover:bg-blue-100"
            onClick={() => handleAnnotationSubmit(1)}
            disabled={isAnnotating}
          >
            <ThumbsUp className="h-4 w-4 mr-1" />
            Annotate with reward 1
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="bg-gray-100 text-gray-600 hover:bg-gray-200"
            onClick={() => handleAnnotationSubmit(0)}
            disabled={isAnnotating}
          >
            <ThumbsDown className="h-4 w-4 mr-1" />
            Annotate with reward 0
          </Button>
          <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
            <Check className="h-4 w-4 text-green-500" />
          </Button>
          <div className="ml-auto flex items-center gap-2">
            <Button variant="ghost" size="sm" onClick={() => setHideAnnotations(!hideAnnotations)}>
              {hideAnnotations ? "Show Annotations" : "Hide Annotations"}
            </Button>
          </div>
        </div>

        {annotationError && <div className="text-red-500 text-sm">{annotationError}</div>}
        {deleteError && <div className="text-red-500 text-sm w-full">{deleteError}</div>}
        {annotationDeleteError && <div className="text-red-500 text-sm w-full">{annotationDeleteError}</div>}

        {!hideAnnotations && response.annotations.length > 0 && (
          <div className="w-full">
            {response.annotations.map((annotation) => (
              <div key={annotation.id} className="flex items-center justify-between py-1 border-t text-sm">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="font-medium">Reward: {annotation.reward}</span>
                  <span className="text-gray-500">By: {annotation.by}</span>
                  <span className="text-gray-500">At: {new Date(annotation.at).toLocaleString()}</span>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-6 w-6 p-0"
                  onClick={() => handleDeleteAnnotation(annotation.id)}
                  disabled={deletingAnnotationId === annotation.id || isAnnotating}
                  title="Delete this annotation"
                >
                  {deletingAnnotationId === annotation.id ? (
                    <RefreshCw className="h-3.5 w-3.5 text-gray-500 animate-spin" />
                  ) : (
                    <X className="h-3.5 w-3.5 text-red-500" />
                  )}
                </Button>
              </div>
            ))}
          </div>
        )}

        {!hideAnnotations && response.annotations.length === 0 && (
          <div className="w-full border-t pt-2 text-sm text-gray-500 italic">No annotations found.</div>
        )}
      </CardFooter>
    </Card>
  )
}
