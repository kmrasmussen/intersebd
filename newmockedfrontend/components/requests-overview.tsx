"use client"

import { useState } from "react"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import Link from "next/link"
import { ChevronRight } from "lucide-react"

// Mock data for the requests
const mockRequests = [
  {
    id: "f3ef3f5e-09c2-4a30-82a2-ecf4f460a1d9",
    name: "What is 2+12?",
    question: "What is 2+12?",
    totalResponses: 10,
    annotatedResponses: 8,
    timestamp: "2025-04-19T11:22:44.054152Z",
  },
  {
    id: "a1b2c3d4-5e6f-7g8h-9i0j-klmno1p2q3r4",
    name: "Explain quantum computing",
    question:
      "Can you explain quantum computing in simple terms? I'm trying to understand how it differs from classical computing and why it's considered revolutionary...",
    totalResponses: 15,
    annotatedResponses: 12,
    timestamp: "2025-04-18T15:30:22.123456Z",
  },
  {
    id: "5e6f7g8h-9i0j-klmn-o1p2-q3r4s5t6u7v8",
    name: "Python code review",
    question:
      "Can you review this Python function that calculates Fibonacci numbers? I think it's inefficient but I'm not sure how to optimize it.",
    totalResponses: 8,
    annotatedResponses: 5,
    timestamp: "2025-04-17T09:45:11.987654Z",
  },
  {
    id: "9i0jklmn-o1p2-q3r4-s5t6-u7v8w9x0y1z2",
    name: "Summarize article",
    question: "Please summarize this article about climate change and provide the key points that I should remember.",
    totalResponses: 12,
    annotatedResponses: 7,
    timestamp: "2025-04-16T14:20:33.456789Z",
  },
  {
    id: "q3r4s5t6-u7v8-w9x0-y1z2-a3b4c5d6e7f8",
    name: "Translation request",
    question: "Can you translate this paragraph from English to Spanish? I need it for my presentation tomorrow.",
    totalResponses: 6,
    annotatedResponses: 6,
    timestamp: "2025-04-15T17:55:42.234567Z",
  },
]

export function RequestsOverview() {
  const [requests] = useState(mockRequests)

  return (
    <div className="rounded-md border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-[100px]">ID</TableHead>
            <TableHead className="w-[200px]">Name</TableHead>
            <TableHead>Question</TableHead>
            <TableHead className="w-[150px]">Responses</TableHead>
            <TableHead className="w-[120px]">Date</TableHead>
            <TableHead className="w-[50px]"></TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {requests.map((request) => (
            <TableRow key={request.id} className="h-12 hover:bg-gray-50">
              <TableCell className="font-mono text-xs text-gray-500">{request.id.substring(0, 8)}...</TableCell>
              <TableCell className="font-medium">{request.name}</TableCell>
              <TableCell className="truncate max-w-[400px]">{request.question}</TableCell>
              <TableCell>
                <Badge variant="outline" className="bg-gray-50">
                  {request.annotatedResponses}/{request.totalResponses}
                </Badge>
              </TableCell>
              <TableCell className="text-gray-500 text-sm">
                {new Date(request.timestamp).toLocaleDateString()}
              </TableCell>
              <TableCell>
                <Link href={`/requests/${request.id}`} className="block">
                  <ChevronRight className="h-5 w-5 text-gray-400" />
                </Link>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}
