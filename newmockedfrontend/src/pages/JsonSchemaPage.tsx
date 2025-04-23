"use client"

import { useState, useEffect } from "react"
import { useParams } from "react-router-dom"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { SchemaValidator } from "@/components/schema-validator"
import { SchemaVersionsList } from "@/components/schema-versions-list"
import { Clock, Play, AlertCircle } from "lucide-react"
import { SchemaEditorComponent } from "@/components/schema-editor-component"

// Default schema template - can be empty now
const initialSchemaValue = ""; // Start with empty string

export default function JsonSchemaPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const [isValidating, setIsValidating] = useState(false)
  const [currentSchema, setCurrentSchema] = useState(initialSchemaValue)
  const [isViewingOldSchema, setIsViewingOldSchema] = useState(false)
  const [isLoadingSchema, setIsLoadingSchema] = useState(true)
  const [schemaError, setSchemaError] = useState<string | null>(null)
  const [isSchemaEmptyState, setIsSchemaEmptyState] = useState(false) // New state flag

  useEffect(() => {
    if (!projectId) return

    const fetchCurrentSchema = async () => {
      setIsLoadingSchema(true)
      setSchemaError(null)
      setIsSchemaEmptyState(false) // Reset empty state on fetch start
      const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || ""
      const GUEST_USER_ID_HEADER = "X-Guest-User-Id"
      const apiUrl = `${API_BASE_URL}/mock-next/${projectId}/schemas/current`
      const guestUserId = localStorage.getItem("guestUserId")
      const headers: HeadersInit = {}
      if (guestUserId) {
        headers[GUEST_USER_ID_HEADER] = guestUserId
      }

      console.log(`Fetching current schema from ${apiUrl}`)

      try {
        const response = await fetch(apiUrl, { headers })

        if (!response.ok) {
          if (response.status === 404) {
            setSchemaError("No active schema found for this project. You can create one below.")
            setCurrentSchema(initialSchemaValue) // Set to empty string
            setIsSchemaEmptyState(true) // Set empty state flag
          } else {
            let errorDetail = `HTTP error! status: ${response.status}`
            try {
              const errorData = await response.json()
              errorDetail += ` - ${errorData.detail || "Unknown error"}`
            } catch {
              /* Ignore */
            }
            throw new Error(errorDetail)
          }
        } else {
          const schemaData = await response.json()
          setCurrentSchema(JSON.stringify(schemaData.schema_content, null, 2))
          setIsSchemaEmptyState(false) // Ensure empty state is false if schema loaded
        }
      } catch (error: any) {
        console.error("Failed to fetch current schema:", error)
        setSchemaError(error.message || "Failed to load schema")
        setCurrentSchema(initialSchemaValue) // Set to empty on error
        setIsSchemaEmptyState(true) // Treat error state as empty for editor placeholder
      } finally {
        setIsLoadingSchema(false)
      }
    }

    fetchCurrentSchema()
  }, [projectId])

  const handleValidate = () => {
    setIsValidating(true)
    setTimeout(() => {
      setIsValidating(false)
    }, 1000)
  }

  const handleSchemaSaved = (newSchemaData: any) => {
    try {
      setCurrentSchema(JSON.stringify(newSchemaData.schema_content, null, 2))
      setIsViewingOldSchema(false)
      setIsSchemaEmptyState(false) // No longer in empty state after saving
    } catch (error) {
      console.error("Error formatting saved schema:", error)
    }
  }

  const handleViewSchemaVersion = () => {
    // Placeholder for viewing schema versions
  }

  return (
    <div className="container mx-auto py-4">
      <h1 className="text-2xl font-bold mb-6">JSON Schema Editor</h1>

      {isLoadingSchema && <div>Loading schema...</div>}
      {schemaError && !isLoadingSchema && (
        <div className="mb-4 p-3 rounded-md bg-red-50 border border-red-200 text-red-700 flex items-center gap-2">
          <AlertCircle className="h-4 w-4" />
          <span>{schemaError}</span>
        </div>
      )}

      {!projectId ? (
        <div>Loading project details...</div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            <SchemaEditorComponent
              projectId={projectId}
              initialSchema={currentSchema}
              onSchemaSaved={handleSchemaSaved}
              isViewingOldSchema={isViewingOldSchema}
              setIsViewingOldSchema={setIsViewingOldSchema}
              isEmptyState={isSchemaEmptyState} // Pass empty state flag
            />

            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-lg">Schema Tryout</CardTitle>
                <Button onClick={handleValidate} disabled={isValidating} className="gap-2 bg-black hover:bg-gray-800">
                  <Play className="h-4 w-4" />
                  {isValidating ? "Validating..." : "Try Against Schema"}
                </Button>
              </CardHeader>
              <CardContent>
                <SchemaValidator schema={currentSchema} onValidate={handleValidate} />
              </CardContent>
            </Card>
          </div>

          <div>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-lg">Schema Versions</CardTitle>
                <Badge variant="outline" className="gap-1">
                  <Clock className="h-3 w-3" />
                  <span>History</span>
                </Badge>
              </CardHeader>
              <CardContent>
                <SchemaVersionsList onViewSchema={handleViewSchemaVersion} />
              </CardContent>
            </Card>
          </div>
        </div>
      )}
    </div>
  )
}
