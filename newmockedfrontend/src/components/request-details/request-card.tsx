"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader } from "@/components/ui/card" // Corrected path
import { Button } from "@/components/ui/button" // Corrected path
import { Badge } from "@/components/ui/badge" // Corrected path
import { RefreshCw, Trash2 } from "lucide-react"

type Message = {
  role: string
  content: string
}

type Request = {
  id: string
  request_log_id: string
  intercept_key: string
  messages: Message[]
  model: string
  response_format: any
  request_timestamp: string
}

export function RequestCard({ request }: { request: Request }) {
  const [showRawRequest, setShowRawRequest] = useState(false)

  const handleDeleteRequest = () => {
    // In a real application, this would make an API call to delete the request
    console.log("Delete request:", request.id)
  }

  return (
    <Card className="border-gray-200">
      <CardHeader className="bg-gray-50 py-3 px-4 border-b">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="bg-gray-100">
              Request
            </Badge>
            <span className="text-sm text-gray-500">{new Date(request.request_timestamp).toLocaleString()}</span>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={() => setShowRawRequest(!showRawRequest)}>
              Raw
            </Button>
            <Button variant="outline" size="sm">
              <RefreshCw className="h-3.5 w-3.5" />
            </Button>
            <Button variant="outline" size="sm" className="text-red-600 hover:bg-red-50" onClick={handleDeleteRequest}>
              <Trash2 className="h-3.5 w-3.5" />
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="p-4">
        {showRawRequest ? (
          <pre className="bg-gray-50 p-3 rounded-md overflow-auto text-xs font-mono">
            {JSON.stringify(request, null, 2)}
          </pre>
        ) : (
          <div className="space-y-3">
            <div>
              <span className="text-sm font-medium text-gray-500">Model:</span>
              <span className="ml-2">{request.model}</span>
            </div>
            <div className="space-y-3">
              <span className="text-sm font-medium text-gray-500">Conversation:</span>
              <div className="space-y-3">
                {request.messages.map((message, index) => (
                  <div
                    key={index}
                    className={`p-3 rounded-md ${
                      message.role === "system"
                        ? "bg-gray-100 border border-gray-200"
                        : message.role === "user"
                          ? "bg-blue-50 border border-blue-100"
                          : "bg-green-50 border border-green-100"
                    }`}
                  >
                    <div className="flex items-center mb-1">
                      <Badge
                        variant="outline"
                        className={`text-xs ${
                          message.role === "system"
                            ? "bg-gray-200 text-gray-700"
                            : message.role === "user"
                              ? "bg-blue-100 text-blue-700"
                              : "bg-green-100 text-green-700"
                        }`}
                      >
                        {message.role}
                      </Badge>
                    </div>
                    <p className="whitespace-pre-wrap">{message.content}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
