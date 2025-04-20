"use client"

import { useState, useRef, useEffect } from "react"
import { Copy, CheckCircle2 } from "lucide-react"
import { Button } from "@/components/ui/button"

interface SchemaEditorProps {
  schema: string
  onChange: (value: string) => void
}

export function SchemaEditor({ schema, onChange }: SchemaEditorProps) {
  const [copied, setCopied] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(schema)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000) // Reset after 2 seconds
    } catch (err) {
      console.error("Failed to copy text: ", err)
    }
  }

  // Format JSON on demand
  const formatJson = () => {
    try {
      const formatted = JSON.stringify(JSON.parse(schema), null, 2)
      onChange(formatted)
    } catch (err) {
      console.error("Failed to format JSON:", err)
    }
  }

  // Adjust textarea height to fit content
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto"
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`
    }
  }, [schema])

  return (
    <div className="relative">
      <div className="absolute top-2 right-2 z-10 flex gap-2">
        <Button
          variant="ghost"
          size="sm"
          className="h-7 px-2 bg-gray-100 hover:bg-gray-200 rounded-md text-xs"
          onClick={formatJson}
        >
          Format
        </Button>
        <Button
          variant="ghost"
          size="sm"
          className="h-7 w-7 p-0 bg-gray-100 hover:bg-gray-200 rounded-md"
          onClick={handleCopy}
          title="Copy Schema"
        >
          {copied ? <CheckCircle2 className="h-4 w-4 text-green-500" /> : <Copy className="h-4 w-4 text-gray-500" />}
          <span className="sr-only">Copy Schema</span>
        </Button>
      </div>

      <textarea
        ref={textareaRef}
        value={schema}
        onChange={(e) => onChange(e.target.value)}
        className="w-full h-auto min-h-[400px] p-4 font-mono text-sm border rounded-md resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
        spellCheck="false"
        aria-label="JSON Schema Editor"
      />
    </div>
  )
}
