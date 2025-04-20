"use client"

import { useState } from "react"
import { Badge } from "@/components/ui/badge" // Corrected path
import { Button } from "@/components/ui/button" // Corrected path
import { ArrowUpDown, Check, Eye } from "lucide-react"

// Mock data for schema versions
const mockSchemaVersions = [
  {
    id: "v1.0.3",
    name: "Production Schema v1.0.3",
    timestamp: "2025-04-19T14:30:00Z",
    author: "admin@example.com",
    isActive: true,
    schema: `{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["result"],
  "properties": {
    "result": {
      "type": "number",
      "description": "The result of the calculation"
    }
  }
}`,
  },
  {
    id: "v1.0.2",
    name: "Production Schema v1.0.2",
    timestamp: "2025-04-15T10:45:00Z",
    author: "admin@example.com",
    isActive: false,
    schema: `{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["result"],
  "properties": {
    "result": {
      "type": "number",
      "description": "The result of the calculation",
      "minimum": 0
    }
  }
}`,
  },
  {
    id: "v1.0.1",
    name: "Initial Schema",
    timestamp: "2025-04-10T09:20:00Z",
    author: "admin@example.com",
    isActive: false,
    schema: `{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["results"],
  "properties": {
    "results": {
      "type": "number",
      "description": "The result of the calculation"
    }
  }
}`,
  },
  {
    id: "v0.9.0",
    name: "Beta Schema",
    timestamp: "2025-04-05T16:15:00Z",
    author: "developer@example.com",
    isActive: false,
    schema: `{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "result": {
      "type": "number"
    }
  }
}`,
  },
  {
    id: "v0.5.0",
    name: "Alpha Schema",
    timestamp: "2025-03-28T11:30:00Z",
    author: "developer@example.com",
    isActive: false,
    schema: `{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "answer": {
      "type": "number"
    }
  }
}`,
  },
]

interface SchemaVersionsListProps {
  onViewSchema?: (schema: string, isActive: boolean) => void
}

export function SchemaVersionsList({ onViewSchema }: SchemaVersionsListProps) {
  const [versions] = useState(mockSchemaVersions)
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc")
  const [selectedVersion, setSelectedVersion] = useState<string | null>(null)

  const toggleSortOrder = () => {
    setSortOrder(sortOrder === "asc" ? "desc" : "asc")
  }

  const handleViewSchema = (version: (typeof mockSchemaVersions)[0]) => {
    setSelectedVersion(version.id)
    if (onViewSchema) {
      onViewSchema(version.schema, version.isActive)
    }
  }

  const sortedVersions = [...versions].sort((a, b) => {
    const dateA = new Date(a.timestamp).getTime()
    const dateB = new Date(b.timestamp).getTime()
    return sortOrder === "asc" ? dateA - dateB : dateB - dateA
  })

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm text-gray-500">Version History</span>
        <Button variant="ghost" size="sm" onClick={toggleSortOrder} className="h-8 px-2">
          <ArrowUpDown className="h-4 w-4 mr-1" />
          {sortOrder === "asc" ? "Oldest first" : "Newest first"}
        </Button>
      </div>

      <div className="space-y-3">
        {sortedVersions.map((version) => (
          <div
            key={version.id}
            className={`p-3 rounded-md border cursor-pointer transition-colors ${
              version.isActive
                ? "bg-blue-50 border-blue-200"
                : selectedVersion === version.id
                  ? "bg-gray-100 border-gray-300"
                  : "bg-white hover:bg-gray-50"
            }`}
            onClick={() => handleViewSchema(version)}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="font-medium">{version.name}</span>
                {version.isActive && (
                  <Badge variant="outline" className="bg-blue-100 text-blue-700 border-blue-200">
                    <Check className="h-3 w-3 mr-1" />
                    Active
                  </Badge>
                )}
                {selectedVersion === version.id && !version.isActive && (
                  <Badge variant="outline" className="bg-gray-100 text-gray-700 border-gray-300">
                    <Eye className="h-3 w-3 mr-1" />
                    Viewing
                  </Badge>
                )}
              </div>
            </div>

            <div className="mt-2 text-sm text-gray-500">
              <div className="flex items-center justify-between">
                <span>ID: {version.id}</span>
                <span>{new Date(version.timestamp).toLocaleString()}</span>
              </div>
              <div className="mt-1">
                <span>Author: {version.author}</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
