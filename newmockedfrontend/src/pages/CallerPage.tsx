"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button" // Corrected path
import { CheckCircle2, Copy } from "lucide-react"
import { CodeExample } from "@/components/code-example" // Corrected path
import { useParams } from "react-router-dom" // Import useParams

export default function CallerPage() {
  const { projectId } = useParams<{ projectId: string }>() // Get projectId from URL

  if (!projectId) {
    // Handle case where projectId is not available (optional, depends on routing setup)
    return <div>Error: Project ID not found in URL.</div>
  }

  const [copied, setCopied] = useState<string | null>(null)

  const endpoint = "http://localhost:9003/v1/chat/completions"
  const apiKey = "sk-intercebd-v1-MYteQu40Bvr1nO04onvzOLZIpzBNv8t4qwMDO0hL3hSzCGw2kyHw"

  const handleCopy = async (text: string, id: string) => {
    await navigator.clipboard.writeText(text)
    setCopied(id)
    setTimeout(() => setCopied(null), 2000)
  }

  return (
    <div className="p-4 md:p-6">
      <h1 className="text-2xl font-semibold mb-4">API Caller</h1>
      <p className="mb-6 text-gray-600">
        Use the code examples below to integrate the API into your application.
        The API key provided is specific to this project.
      </p>

      {/* *** Pass projectId to CodeExample *** */}
      <CodeExample projectId={projectId} title="Chat Completions Example" />

      {/* Configuration Fields */}
      <div className="space-y-4 mt-8">
        <div>
          <h2 className="text-lg font-medium mb-2">Chat Completions Endpoint</h2>
          <div className="relative">
            <div className="p-3 bg-gray-50 border rounded-md font-mono text-sm overflow-x-auto">{endpoint}</div>
            <Button
              variant="ghost"
              size="sm"
              className="absolute top-2 right-2 h-8 w-8 p-0"
              onClick={() => handleCopy(endpoint, "endpoint")}
            >
              {copied === "endpoint" ? (
                <CheckCircle2 className="h-4 w-4 text-green-500" />
              ) : (
                <Copy className="h-4 w-4" />
              )}
              <span className="sr-only">Copy endpoint</span>
            </Button>
          </div>
        </div>

        <div>
          <h2 className="text-lg font-medium mb-2">Guest API Key (Secret for non-guests):</h2>
          <div className="relative">
            <div className="p-3 bg-gray-50 border rounded-md font-mono text-sm overflow-x-auto">{apiKey}</div>
            <Button
              variant="ghost"
              size="sm"
              className="absolute top-2 right-2 h-8 w-8 p-0"
              onClick={() => handleCopy(apiKey, "apiKey")}
            >
              {copied === "apiKey" ? <CheckCircle2 className="h-4 w-4 text-green-500" /> : <Copy className="h-4 w-4" />}
              <span className="sr-only">Copy API key</span>
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}
