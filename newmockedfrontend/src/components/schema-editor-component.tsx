"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Save, ChevronUp, ChevronDown } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { SchemaEditor } from "@/components/schema-editor"

interface SchemaEditorComponentProps {
  className?: string
  title?: string
}

// Initial schema template
const initialSchema = `{
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

export function SchemaEditorComponent({ className = "", title = "Edit Schema" }: SchemaEditorComponentProps) {
  const [schema, setSchema] = useState(initialSchema)
  const [isSaving, setIsSaving] = useState(false)
  const [isViewingOldSchema, setIsViewingOldSchema] = useState(false)
  const [collapsed, setCollapsed] = useState(false)

  const handleSave = () => {
    setIsSaving(true)
    // Simulate API call
    setTimeout(() => {
      setIsSaving(false)
      setIsViewingOldSchema(false)
      // In a real app, we would save the schema to the backend
      console.log("Schema saved:", schema)
    }, 1000)
  }

  const toggleCollapse = () => {
    setCollapsed(!collapsed)
  }

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
        </div>
        <div className="flex items-center gap-2">
          {!collapsed && (
            <Button onClick={handleSave} disabled={isSaving} className="gap-2 bg-black hover:bg-gray-800">
              <Save className="h-4 w-4" />
              {isSaving ? "Saving..." : isViewingOldSchema ? "Save as New Version" : "Save Schema"}
            </Button>
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
          <SchemaEditor schema={schema} onChange={setSchema} />
        </CardContent>
      )}
    </Card>
  )
}
