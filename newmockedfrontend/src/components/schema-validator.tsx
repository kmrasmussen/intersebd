"use client"

import { useState, useRef, useEffect } from "react"
import { Copy, CheckCircle2, AlertCircle } from "lucide-react"
import { Button } from "@/components/ui/button" // Corrected path
import { Badge } from "@/components/ui/badge" // Corrected path
import Ajv, { type ErrorObject } from "ajv" // Import AJV and ErrorObject type

interface SchemaValidatorProps {
  schema: string; // Add schema prop
  onValidate: (isValid: boolean, errors?: ErrorObject[] | null | undefined) => void; // Use ErrorObject type directly
}

export function SchemaValidator({ schema, onValidate }: SchemaValidatorProps) { // Destructure props
  const [jsonInput, setJsonInput] = useState('{\n  "result": 42\n}')
  const [copied, setCopied] = useState(false)
  const [validationResult, setValidationResult] = useState<{
    valid: boolean
    message?: string
  } | null>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const ajv = new Ajv() // Initialize AJV

  const handleValidateClick = () => {
    try {
      const parsedSchema = JSON.parse(schema)
      const validate = ajv.compile(parsedSchema)
      const parsedJsonInput = JSON.parse(jsonInput)
      const isValid = validate(parsedJsonInput)

      if (isValid) {
        setValidationResult({ valid: true })
        onValidate(true)
      } else {
        const errorMessages = validate.errors?.map(err => `${err.instancePath || "input"} ${err.message}`).join(", ")
        setValidationResult({ valid: false, message: errorMessages || "Invalid JSON against schema" })
        onValidate(false, validate.errors)
      }
    } catch (error: any) {
      let errorMessage = "Validation failed"
      if (error instanceof SyntaxError) {
        errorMessage = `Invalid JSON or Schema: ${error.message}`
      } else if (error.message) {
        errorMessage = error.message
      }
      setValidationResult({ valid: false, message: errorMessage })
      onValidate(false)
      console.error("Validation error:", error)
    }
  }

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

      {/* Button to trigger validation - added onClick handler */}
      <Button onClick={handleValidateClick} className="mt-2">
        Validate JSON
      </Button>

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
