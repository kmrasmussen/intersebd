"use client"

import { useState } from "react"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Copy, CheckCircle2, ChevronUp, ChevronDown, Maximize2, Minimize2 } from "lucide-react"

interface CodeExampleProps {
  defaultPrompt?: string
  className?: string
  title?: string
}

export function CodeExample({
  defaultPrompt = "What is 2+2?",
  className = "",
  title = "Code Example",
}: CodeExampleProps) {
  const [language, setLanguage] = useState<"curl" | "python" | "javascript">("python")
  const [prompt, setPrompt] = useState(defaultPrompt)
  const [copied, setCopied] = useState(false)
  const [collapsed, setCollapsed] = useState(false)
  const [expandedInput, setExpandedInput] = useState(false)

  const endpoint = "http://localhost:9003/v1/chat/completions"
  const apiKey = "sk-intercebd-v1-MYteQu40Bvr1nO04onvzOLZIpzBNv8t4qwMDO0hL3hSzCGw2kyHw"

  const handleCopy = async () => {
    await navigator.clipboard.writeText(getCodeSnippet())
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleRun = () => {
    // In a real app, this would make an actual API call
    console.log("Running with prompt:", prompt)
  }

  const toggleCollapse = () => {
    setCollapsed(!collapsed)
  }

  const toggleExpandInput = () => {
    setExpandedInput(!expandedInput)
  }

  const getCodeSnippet = () => {
    switch (language) {
      case "curl":
        return `curl ${endpoint} \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer ${apiKey}" \\
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
  baseURL: "http://localhost:9003/v1",
  apiKey: "${apiKey}"
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
    base_url="http://localhost:9003/v1",
    api_key="${apiKey}"
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

  return (
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
          <Tabs defaultValue="python" value={language} onValueChange={(value) => setLanguage(value as any)}>
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
            <Button variant="ghost" size="sm" className="absolute top-2 right-2 h-8 w-8 p-0" onClick={handleCopy}>
              {copied ? <CheckCircle2 className="h-4 w-4 text-green-500" /> : <Copy className="h-4 w-4" />}
              <span className="sr-only">Copy code</span>
            </Button>
          </div>

          <div className="flex flex-col md:flex-row gap-4 mt-4">
            <Button onClick={handleRun} className="md:w-auto">
              Run call shown above
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
  )
}
