"use client"

import { useState, useRef, useEffect } from "react"
import { Copy, CheckCircle2, AlertCircle } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"

interface SchemaValidatorProps {
  schema: string
  onValidate?: () => void
}

export function SchemaValidator({ schema, onValidate }: SchemaValidatorProps) {
  const [jsonInput, setJsonInput] = useState('{\n  "result": 42\n}')
  const [copied, setCopied] = useState(false)
  const [validationResult, setValidationResult] = useState<{
    valid: boolean
    message?: string
  } | null>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(jsonInput)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000) // Reset after 2 seconds
    } catch (err) {
      console.error("Failed to copy text: ", err)
    }
  }

  // Format JSON on demand
  const formatJson = () => {
    try {
      const formatted = JSON.stringify(JSON.parse(jsonInput), null, 2)
      setJsonInput(formatted)
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
  }, [jsonInput])

  const validateJson = () => {
    try {
      // Parse the JSON input
      const jsonData = JSON.parse(jsonInput)

      // Parse the schema
      const schemaData = JSON.parse(schema)

      // Basic validation (this is a simplified version)
      let isValid = true
      let errorMessage = ""

      // Check required properties
      if (schemaData.required && Array.isArray(schemaData.required)) {
        for (const requiredProp of schemaData.required) {
          if (!(requiredProp in jsonData)) {
            isValid = false
            errorMessage = `Required property "${requiredProp}" is missing`
            break
          }
        }
      }

      // Check property types if we have properties defined
      if (isValid && schemaData.properties) {
        for (const [propName, propSchema] of Object.entries(schemaData.properties)) {
          if (propName in jsonData) {
            const propValue = jsonData[propName]
            const propType = (propSchema as any).type

            // Check type
            if (propType === "string" && typeof propValue !== "string") {
              isValid = false
              errorMessage = `Property "${propName}" should be a string`
              break
            } else if (propType === "number" && typeof propValue !== "number") {
              isValid = false
              errorMessage = `Property "${propName}" should be a number`
              break
            } else if (propType === "boolean" && typeof propValue !== "boolean") {
              isValid = false
              errorMessage = `Property "${propName}" should be a boolean`
              break
            } else if (
              propType === "object" &&
              (typeof propValue !== "object" || propValue === null || Array.isArray(propValue))
            ) {
              isValid = false
              errorMessage = `Property "${propName}" should be an object`
              break
            } else if (propType === "array" && !Array.isArray(propValue)) {
              isValid = false
              errorMessage = `Property "${propName}" should be an array`
              break
            }
          }
        }
      }

      setValidationResult({ valid: isValid, message: errorMessage })
      if (onValidate) onValidate()
    } catch (e) {
      setValidationResult({
        valid: false,
        message: e instanceof Error ? e.message : "Invalid JSON",
      })
    }
  }

  return (
    <div className="space-y-4">
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
            title="Copy JSON"
          >
            {copied ? <CheckCircle2 className="h-4 w-4 text-green-500" /> : <Copy className="h-4 w-4 text-gray-500" />}
            <span className="sr-only">Copy JSON</span>
          </Button>
        </div>

        <textarea
          ref={textareaRef}
          value={jsonInput}
          onChange={(e) => setJsonInput(e.target.value)}
          className="w-full h-auto min-h-[200px] p-4 font-mono text-sm border rounded-md resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
          spellCheck="false"
          aria-label="JSON Input"
        />
      </div>

      {validationResult && (
        <div
          className={`p-3 rounded-md ${validationResult.valid ? "bg-green-50 border border-green-200" : "bg-red-50 border border-red-200"}`}
        >
          <div className="flex items-center gap-2">
            {validationResult.valid ? (
              <>
                <Badge variant="outline" className="bg-green-100 text-green-700 border-green-200">
                  Valid
                </Badge>
                <span className="text-green-700">JSON is valid against the schema</span>
              </>
            ) : (
              <>
                <Badge variant="outline" className="bg-red-100 text-red-700 border-red-200">
                  Invalid
                </Badge>
                <span className="text-red-700">{validationResult.message || "JSON is invalid against the schema"}</span>
                <AlertCircle className="h-4 w-4 text-red-500" />
              </>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
