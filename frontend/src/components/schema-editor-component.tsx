"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Save, ChevronUp, ChevronDown, AlertCircle, CheckCircle2, Trash2 } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { SchemaEditor } from "@/components/schema-editor"

interface SchemaEditorComponentProps {
  className?: string
  title?: string
  projectId: string
  initialSchema?: string
  onSchemaSaved?: (newSchemaData: any | null) => void
  isViewingOldSchema?: boolean
  setIsViewingOldSchema?: (isViewing: boolean) => void
  isEmptyState?: boolean
  hasActiveSchema?: boolean
}

const defaultSchema = `{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["result"],
  "properties": {
    "result": {
      "type": "number",
      "description": "The result of the calculation"
    }
  }
}`

const emptySchemaPlaceholder = "// Enter your JSON schema here..."

export function SchemaEditorComponent({
  className = "",
  title = "Edit Schema",
  projectId,
  initialSchema = defaultSchema,
  onSchemaSaved,
  isViewingOldSchema = false,
  setIsViewingOldSchema,
  isEmptyState = false,
  hasActiveSchema = false,
}: SchemaEditorComponentProps) {
  const [schema, setSchema] = useState(initialSchema)
  const [isSaving, setIsSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [saveSuccess, setSaveSuccess] = useState(false)
  const [collapsed, setCollapsed] = useState(false)

  const [isRemoving, setIsRemoving] = useState(false)
  const [removeError, setRemoveError] = useState<string | null>(null)
  const [removeSuccess, setRemoveSuccess] = useState(false)

  useEffect(() => {
    setSchema(initialSchema)
  }, [initialSchema])

  const handleSave = async () => {
    setIsSaving(true)
    setSaveError(null)
    setSaveSuccess(false)
    setRemoveError(null)

    const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || ""
    const GUEST_USER_ID_HEADER = "X-Guest-User-Id"
    const apiUrl = `${API_BASE_URL}/mock-next/${projectId}/schemas`
    const guestUserId = localStorage.getItem("guestUserId")
    const headers: HeadersInit = {
      "Content-Type": "application/json",
    }
    if (guestUserId) {
      headers[GUEST_USER_ID_HEADER] = guestUserId
    }

    let parsedSchemaContent
    try {
      parsedSchemaContent = JSON.parse(schema)
    } catch (error) {
      setSaveError("Invalid JSON: Cannot save schema. Please fix syntax errors.")
      setIsSaving(false)
      return
    }

    console.log(`Saving schema for project ${projectId} at ${apiUrl}`)

    try {
      const response = await fetch(apiUrl, {
        method: "POST",
        headers: headers,
        body: JSON.stringify({ schema_content: parsedSchemaContent }),
        credentials: "include",
      })

      if (!response.ok) {
        let errorDetail = `HTTP error! status: ${response.status}`
        try {
          const errorData = await response.json()
          errorDetail += ` - ${errorData.detail || "Unknown error"}`
        } catch (jsonError) {}
        throw new Error(errorDetail)
      }

      const savedSchemaData = await response.json()
      console.log("Schema saved successfully:", savedSchemaData)

      setSaveSuccess(true)
      setTimeout(() => setSaveSuccess(false), 3000)

      if (isViewingOldSchema && setIsViewingOldSchema) {
        setIsViewingOldSchema(false)
      }
      if (onSchemaSaved) {
        onSchemaSaved(savedSchemaData)
      }
    } catch (error: any) {
      console.error("Failed to save schema:", error)
      setSaveError(error.message || "Failed to save schema")
    } finally {
      setIsSaving(false)
    }
  }

  const handleRemoveSchema = async () => {
    setIsRemoving(true)
    setRemoveError(null)
    setRemoveSuccess(false)
    setSaveError(null)

    const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || ""
    const GUEST_USER_ID_HEADER = "X-Guest-User-Id"
    const apiUrl = `${API_BASE_URL}/mock-next/${projectId}/schemas/active`
    const guestUserId = localStorage.getItem("guestUserId")
    const headers: HeadersInit = {}
    if (guestUserId) {
      headers[GUEST_USER_ID_HEADER] = guestUserId
    }

    console.log(`Attempting to remove active schema for project ${projectId} at ${apiUrl}`)

    try {
      const response = await fetch(apiUrl, {
        method: "DELETE",
        headers: headers,
        credentials: "include",
      })

      if (response.status === 204) {
        console.log("Active schema removed successfully.")
        setRemoveSuccess(true)
        setSchema(defaultSchema)
        setTimeout(() => setRemoveSuccess(false), 3000)
        if (onSchemaSaved) {
          onSchemaSaved(null)
        }
      } else if (!response.ok) {
        let errorDetail = `HTTP error! status: ${response.status}`
        try {
          const errorData = await response.json()
          errorDetail += ` - ${errorData.detail || "Unknown error"}`
        } catch (jsonError) {}
        throw new Error(errorDetail)
      }
    } catch (error: any) {
      console.error("Failed to remove schema:", error)
      setRemoveError(error.message || "Failed to remove schema")
    } finally {
      setIsRemoving(false)
    }
  }

  const toggleCollapse = () => {
    setCollapsed(!collapsed)
  }

  const isDefaultOrEmpty = schema === defaultSchema || schema === emptySchemaPlaceholder || schema.trim() === ""

  return (
    <Card className={`mb-6 ${className}`}>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <div className="flex items-center gap-2">
          <CardTitle className="text-md font-medium">{title}</CardTitle>
          {isViewingOldSchema && (
            <Badge variant="outline" className="bg-yellow-50 text-yellow-700 border-yellow-200">
              Viewing historical version
            </Badge>
          )}
          {!isViewingOldSchema && !hasActiveSchema && (
            <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200">
              No active schema
            </Badge>
          )}
        </div>
        <div className="flex items-center gap-2">
          {!collapsed && !isViewingOldSchema && (
            <>
              <Button
                onClick={handleSave}
                disabled={isSaving || saveSuccess || isRemoving || removeSuccess}
                className={`gap-2 ${saveSuccess ? "bg-green-600 hover:bg-green-700" : "bg-black hover:bg-gray-800"}`}
              >
                {isSaving ? (
                  <Save className="h-4 w-4 animate-spin" />
                ) : saveSuccess ? (
                  <CheckCircle2 className="h-4 w-4" />
                ) : (
                  <Save className="h-4 w-4" />
                )}
                {isSaving ? "Saving..." : saveSuccess ? "Saved!" : "Save Schema"}
              </Button>
              {hasActiveSchema && (
                <Button
                  variant="outline"
                  onClick={handleRemoveSchema}
                  disabled={isRemoving || removeSuccess || isSaving || saveSuccess}
                  className="gap-2 text-red-600 border-red-300 hover:bg-red-50 hover:text-red-700"
                  title="Remove the current active schema for this project"
                >
                  {isRemoving ? (
                    <Trash2 className="h-4 w-4 animate-spin" />
                  ) : removeSuccess ? (
                    <CheckCircle2 className="h-4 w-4" />
                  ) : (
                    <Trash2 className="h-4 w-4" />
                  )}
                  {isRemoving ? "Removing..." : removeSuccess ? "Removed!" : "Remove Schema"}
                </Button>
              )}
            </>
          )}
          <Button
            variant="ghost"
            size="sm"
            className="h-8 w-8 p-0"
            onClick={toggleCollapse}
            aria-label={collapsed ? "Expand schema editor" : "Collapse schema editor"}
          >
            {collapsed ? <ChevronDown className="h-4 w-4" /> : <ChevronUp className="h-4 w-4" />}
          </Button>
        </div>
      </CardHeader>

      {!collapsed && (
        <CardContent>
          {saveError && (
            <div className="mb-4 p-3 rounded-md bg-red-50 border border-red-200 text-red-700 flex items-center gap-2">
              <AlertCircle className="h-4 w-4" />
              <span>{saveError}</span>
            </div>
          )}
          {removeError && (
            <div className="mb-4 p-3 rounded-md bg-red-50 border border-red-200 text-red-700 flex items-center gap-2">
              <AlertCircle className="h-4 w-4" />
              <span>{removeError}</span>
            </div>
          )}
          <SchemaEditor
            schema={schema}
            onChange={setSchema}
            placeholder={isEmptyState || !hasActiveSchema ? emptySchemaPlaceholder : undefined}
          />
        </CardContent>
      )}
    </Card>
  )
}
