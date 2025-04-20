"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { SchemaValidator } from "@/components/schema-validator"
import { SchemaVersionsList } from "@/components/schema-versions-list"
import { Clock, Play } from "lucide-react"
import { SchemaEditorComponent } from "@/components/schema-editor-component"

export default function JsonSchemaPage() {
  const [isValidating, setIsValidating] = useState(false)

  const handleValidate = () => {
    setIsValidating(true)
    // Reset after a short delay
    setTimeout(() => {
      setIsValidating(false)
    }, 1000)
  }

  return (
    <div className="container mx-auto py-4">
      <h1 className="text-2xl font-bold mb-6">JSON Schema Editor</h1>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <SchemaEditorComponent />

          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-lg">Schema Tryout</CardTitle>
              <Button onClick={handleValidate} disabled={isValidating} className="gap-2 bg-black hover:bg-gray-800">
                <Play className="h-4 w-4" />
                {isValidating ? "Validating..." : "Try Against Schema"}
              </Button>
            </CardHeader>
            <CardContent>
              <SchemaValidator schema={"{}"} onValidate={handleValidate} />
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
              <SchemaVersionsList onViewSchema={() => {}} />
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
