"use client"

import { useState, useEffect } from "react"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogDescription,
    DialogFooter,
    DialogClose,
} from "@/components/ui/dialog"
import { Copy, CheckCircle2, ChevronUp, ChevronDown, Maximize2, Minimize2, AlertCircle, Loader2 } from "lucide-react"

interface KeySchema {
  id: string
  key: string
  project_id: string
  created_at: string
  is_active: boolean
}

interface CodeExampleProps {
  projectId: string
  defaultPrompt?: string
  className?: string
  title?: string
}

export function CodeExample({
  projectId,
  defaultPrompt = "What is 2+2?",
  className = "",
  title = "Code Example",
}: CodeExampleProps) {
  const [language, setLanguage] = useState<"curl" | "python" | "javascript">("python")
  const [prompt, setPrompt] = useState(defaultPrompt)
  const [copied, setCopied] = useState(false)
  const [collapsed, setCollapsed] = useState(false)
  const [expandedInput, setExpandedInput] = useState(false)

  const [apiKey, setApiKey] = useState<string | null>(null)
  const [isLoadingKey, setIsLoadingKey] = useState(true)
  const [keyError, setKeyError] = useState<string | null>(null)

  const [isCallingApi, setIsCallingApi] = useState(false)
  const [apiResponse, setApiResponse] = useState<any>(null)
  const [apiError, setApiError] = useState<string | null>(null)
  const [isResponseDialogOpen, setIsResponseDialogOpen] = useState(false)

  const endpoint = `${import.meta.env.VITE_API_BASE_URL || ""}/v1/chat/completions`

  useEffect(() => {
    const fetchApiKey = async () => {
      if (!projectId) {
        setKeyError("Project ID is missing.")
        setIsLoadingKey(false)
        return
      }
      setIsLoadingKey(true)
      setKeyError(null)
      try {
        const baseUrl = import.meta.env.VITE_API_BASE_URL || ""
        const keyUrl = `${baseUrl}/completion-project-call-keys/${projectId}/some-call-key`
        const response = await fetch(keyUrl, { credentials: "include" })

        if (!response.ok) {
          const errorData = await response.text()
          throw new Error(`Failed to fetch API key (${response.status}): ${errorData}`)
        }
        const data: KeySchema = await response.json()
        if (data && data.key) {
          setApiKey(data.key)
        } else {
          throw new Error("API key not found in response.")
        }
      } catch (e: any) {
        console.error("Error fetching API key:", e)
        setKeyError(e.message || "Failed to load API key.")
      } finally {
        setIsLoadingKey(false)
      }
    }

    fetchApiKey()
  }, [projectId])

  const handleCopy = async () => {
    if (!apiKey) return
    await navigator.clipboard.writeText(getCodeSnippet())
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleRun = async () => {
    if (!apiKey) return

    setIsCallingApi(true)
    setApiResponse(null)
    setApiError(null)
    setIsResponseDialogOpen(true)

    try {
      const requestBody = {
        model: "openai/gpt-4.1-nano",
        messages: [
          {
            role: "user",
            content: prompt,
          },
        ],
      }

      const response = await fetch(endpoint, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${apiKey}`,
        },
        body: JSON.stringify(requestBody),
      })

      const responseData = await response.json()

      if (!response.ok) {
        const errorDetail = responseData?.detail || responseData?.message || JSON.stringify(responseData)
        throw new Error(`API Error (${response.status}): ${errorDetail}`)
      }

      setApiResponse(responseData)
    } catch (error: any) {
      console.error("API Call failed:", error)
      setApiError(error.message || "An unexpected error occurred.")
    } finally {
      setIsCallingApi(false)
    }
  }

  const toggleCollapse = () => {
    setCollapsed(!collapsed)
  }

  const toggleExpandInput = () => {
    setExpandedInput(!expandedInput)
  }

  const getCodeSnippet = () => {
    const effectiveApiKey = apiKey || "YOUR_API_KEY"

    switch (language) {
      case "curl":
        return `curl ${endpoint} \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer ${effectiveApiKey}" \\
  -d '{
    "model": "gpt-4.1-nano",
    "messages": [
      {
        "role": "user",
        "content": "${prompt}"
      }
    ]
  }'`
      case "javascript":
        return `import OpenAI from 'openai';

const client = new OpenAI({
  baseURL: "${import.meta.env.VITE_API_BASE_URL || ""}/v1",
  apiKey: "${effectiveApiKey}"
});

const completion = await client.chat.completions.create({
  model: "openai/gpt-4.1-nano",
  messages: [
    {
      "role": "user",
      "content": \`${prompt}\`
    }
  ]
});

console.log(completion);`
      case "python":
      default:
        return `from openai import OpenAI

client = OpenAI(
    base_url="${import.meta.env.VITE_API_BASE_URL || ""}/v1",
    api_key="${effectiveApiKey}"
)

completion = client.chat.completions.create(
    model="openai/gpt-4.1-nano",
    messages=[
        {
            "role": "user",
            "content": f"""${prompt}"""
        }
    ]
)

print(completion)`
    }
  }

  if (isLoadingKey) {
    return (
      <Card className={`mb-6 ${className}`}>
        <CardHeader className="py-3 px-4">
          <CardTitle className="text-md font-medium">{title}</CardTitle>
        </CardHeader>
        <CardContent>Loading API Key...</CardContent>
      </Card>
    )
  }

  if (keyError) {
    return (
      <Card className={`mb-6 ${className} border-red-500`}>
        <CardHeader className="py-3 px-4 bg-red-50">
          <CardTitle className="text-md font-medium text-red-700 flex items-center">
            <AlertCircle className="h-5 w-5 mr-2" /> Error Loading API Key
          </CardTitle>
        </CardHeader>
        <CardContent className="pt-4 text-red-600">{keyError}</CardContent>
      </Card>
    )
  }

  return (
    <>
      <Card className={`mb-6 ${className}`}>
        <CardHeader className="py-3 px-4 flex flex-row items-center justify-between">
          <CardTitle className="text-md font-medium">{title}</CardTitle>
          <Button
            variant="ghost"
            size="sm"
            className="h-8 w-8 p-0"
            onClick={toggleCollapse}
            aria-label={collapsed ? "Expand code example" : "Collapse code example"}
          >
            {collapsed ? <ChevronDown className="h-4 w-4" /> : <ChevronUp className="h-4 w-4" />}
          </Button>
        </CardHeader>

        {!collapsed && (
          <CardContent className="pt-0">
            <Tabs defaultValue="python" value={language} onValueChange={(value: string) => setLanguage(value as any)}>
              <TabsList className="mb-2">
                <TabsTrigger value="curl">curl</TabsTrigger>
                <TabsTrigger value="python">python</TabsTrigger>
                <TabsTrigger value="javascript">javascript</TabsTrigger>
              </TabsList>
            </Tabs>

            <div className="relative">
              <pre className="p-4 text-sm font-mono bg-gray-50 rounded-md overflow-auto max-h-[400px]">
                {getCodeSnippet()}
              </pre>
              <Button variant="ghost" size="sm" className="absolute top-2 right-2 h-8 w-8 p-0" onClick={handleCopy} disabled={!apiKey}>
                {copied ? <CheckCircle2 className="h-4 w-4 text-green-500" /> : <Copy className="h-4 w-4" />}
                <span className="sr-only">Copy code</span>
              </Button>
            </div>

            <div className="flex flex-col md:flex-row gap-4 mt-4">
              <Button
                onClick={handleRun}
                className="md:w-auto"
                disabled={!apiKey || isCallingApi}
              >
                {isCallingApi ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Running...
                  </>
                ) : (
                  "Run call shown above"
                )}
              </Button>
              <div className="flex-1 relative">
                {expandedInput ? (
                  <div className="relative">
                    <Button
                      variant="ghost"
                      size="sm"
                      className="absolute right-2 top-2 h-8 w-8 p-0 z-10"
                      onClick={toggleExpandInput}
                      aria-label="Collapse input field"
                    >
                      <Minimize2 className="h-4 w-4" />
                    </Button>
                    <textarea
                      value={prompt}
                      onChange={(e) => setPrompt(e.target.value)}
                      className="w-full px-3 pr-10 py-2 border rounded-md resize-vertical"
                      placeholder="Enter your prompt here"
                      rows={10}
                    />
                  </div>
                ) : (
                  <div className="relative">
                    <Button
                      variant="ghost"
                      size="sm"
                      className="absolute right-2 top-1/2 -translate-y-1/2 h-8 w-8 p-0 z-10"
                      onClick={toggleExpandInput}
                      aria-label="Expand input field"
                    >
                      <Maximize2 className="h-4 w-4" />
                    </Button>
                    <input
                      type="text"
                      value={prompt}
                      onChange={(e) => setPrompt(e.target.value)}
                      className="w-full px-3 pr-10 py-2 border rounded-md"
                      placeholder="Enter your prompt here"
                    />
                  </div>
                )}
              </div>
            </div>
          </CardContent>
        )}
      </Card>

      <Dialog open={isResponseDialogOpen} onOpenChange={setIsResponseDialogOpen}>
        <DialogContent className="sm:max-w-[600px]">
          <DialogHeader>
            <DialogTitle>API Call Result</DialogTitle>
            <DialogDescription>
              The response from the API call is shown below.
            </DialogDescription>
          </DialogHeader>
          <div className="mt-4 max-h-[50vh] overflow-y-auto rounded-md border bg-secondary p-4">
            {isCallingApi && (
              <div className="flex items-center justify-center p-8">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
              </div>
            )}
            {apiError && (
              <div className="text-red-600">
                <p className="font-semibold">Error:</p>
                <pre className="mt-1 whitespace-pre-wrap text-sm">{apiError}</pre>
              </div>
            )}
            {apiResponse && (
              <div>
                <p className="font-semibold">Response:</p>
                <pre className="mt-1 whitespace-pre-wrap text-sm">
                  {JSON.stringify(apiResponse, null, 2)}
                </pre>
              </div>
            )}
          </div>
          <DialogFooter>
            <DialogClose asChild>
              <Button type="button" variant="secondary">
                Close
              </Button>
            </DialogClose>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
