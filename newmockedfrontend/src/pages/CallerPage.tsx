"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button" // Corrected path
import { CheckCircle2, Copy } from "lucide-react"
import { CodeExample } from "@/components/code-example" // Corrected path

export default function CallerPage() {
  const [copied, setCopied] = useState<string | null>(null)

  const endpoint = "http://localhost:9003/v1/chat/completions"
  const apiKey = "sk-intercebd-v1-MYteQu40Bvr1nO04onvzOLZIpzBNv8t4qwMDO0hL3hSzCGw2kyHw"

  const handleCopy = async (text: string, id: string) => {
    await navigator.clipboard.writeText(text)
    setCopied(id)
    setTimeout(() => setCopied(null), 2000)
  }

  return (
    <div className="container mx-auto py-4">
      <h1 className="text-2xl font-bold mb-6">Caller</h1>

      <CodeExample defaultPrompt="What is 2+2?" title="API Call Example" />

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
