"use client"

import { useState } from "react"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { ChevronDown, ChevronRight, ArrowRight } from "lucide-react"
import { RequestCard } from "@/components/request-details/request-card"
import { ResponseSection } from "@/components/request-details/response-section"
import { AlternativesSection } from "@/components/request-details/alternatives-section"
import { NewAlternativeForm } from "@/components/request-details/new-alternative-form"
import Link from "next/link"
import { InfoModal } from "@/components/info-modal"

// Mock data for the requests - same as in RequestsOverview
const mockRequests = [
  {
    id: "f3ef3f5e-09c2-4a30-82a2-ecf4f460a1d9",
    name: "What is 2+12?",
    question: "What is 2+12?",
    totalResponses: 10,
    annotatedResponses: 8,
    timestamp: "2025-04-19T11:22:44.054152Z",
    sftStatus: "complete", // complete, partial, none
    dpoStatus: "partial", // complete, partial, none
  },
  {
    id: "a1b2c3d4-5e6f-7g8h-9i0j-klmno1p2q3r4",
    name: "Explain quantum computing",
    question:
      "Can you explain quantum computing in simple terms? I'm trying to understand how it differs from classical computing and why it's considered revolutionary...",
    totalResponses: 15,
    annotatedResponses: 12,
    timestamp: "2025-04-18T15:30:22.123456Z",
    sftStatus: "complete",
    dpoStatus: "complete",
  },
  {
    id: "5e6f7g8h-9i0j-klmn-o1p2-q3r4s5t6u7v8",
    name: "Python code review",
    question:
      "Can you review this Python function that calculates Fibonacci numbers? I think it's inefficient but I'm not sure how to optimize it.",
    totalResponses: 8,
    annotatedResponses: 5,
    timestamp: "2025-04-17T09:45:11.987654Z",
    sftStatus: "partial",
    dpoStatus: "none",
  },
  {
    id: "9i0jklmn-o1p2-q3r4-s5t6-u7v8w9x0y1z2",
    name: "Summarize article",
    question: "Please summarize this article about climate change and provide the key points that I should remember.",
    totalResponses: 12,
    annotatedResponses: 7,
    timestamp: "2025-04-16T14:20:33.456789Z",
    sftStatus: "none",
    dpoStatus: "partial",
  },
  {
    id: "q3r4s5t6-u7v8-w9x0-y1z2-a3b4c5d6e7f8",
    name: "Translation request",
    question: "Can you translate this paragraph from English to Spanish? I need it for my presentation tomorrow.",
    totalResponses: 6,
    annotatedResponses: 6,
    timestamp: "2025-04-15T17:55:42.234567Z",
    sftStatus: "partial",
    dpoStatus: "complete",
  },
]

// Mock data for a single request - same as in RequestDetails
const mockRequestDetails = {
  "f3ef3f5e-09c2-4a30-82a2-ecf4f460a1d9": {
    id: "f3ef3f5e-09c2-4a30-82a2-ecf4f460a1d9",
    name: "What is 2+12?",
    pairNumber: 2,
    request: {
      id: "f3ef3f5e-09c2-4a30-82a2-ecf4f460a1d9",
      request_log_id: "d4d2a938-0e3f-46ba-8414-21d72ae8c807",
      intercept_key: "sk-intercept-v1-JHteQu40BvrlnOD4onvz0LZIpzBNv8t4qwMDO0hL3hSzCGw2kyHw",
      messages: [
        {
          role: "system",
          content: "You are a helpful assistant",
        },
        {
          role: "user",
          content: "What is 2+12?",
        },
      ],
      model: "openai/gpt-4.1-nano",
      response_format: null,
      request_timestamp: "2025-04-19T11:22:44.054152Z",
    },
    mainResponse: {
      id: "gen-1745061763-51UoTnHd5YbhmM8TMKK",
      content: "2 + 12 equals 14.",
      model: "openai/gpt-4.1-nano",
      created: "2025-04-19T14:22:43Z",
      annotations: [
        {
          reward: 1,
          by: "guest-rater",
          at: "2025-04-19T14:25:30Z",
        },
      ],
      metadata: {
        completion_id: "f3ef3f5e-09c2-4a30-82a2-ecf4f460a1d9",
        annotation_target_id: "3b550e5c-9fb0-419c-9739-8106fe0d019c",
        provider: "OpenAI",
        model: "openai/gpt-4.1-nano",
        prompt_tokens: 14,
        completion_tokens: 9,
        total_tokens: 23,
        choice_finish_reason: "stop",
        choice_role: "assistant",
        choice_content: "2 + 12 equals 14.",
      },
      is_json: false,
      obeys_schema: null,
    },
    alternativeResponses: [
      {
        id: "alt-1",
        content: "sdfsad",
        model: "openai/gpt-4.1-nano",
        created: "2025-04-19T14:25:40Z",
        annotations: [],
        is_json: false,
        obeys_schema: null,
      },
      {
        id: "alt-2",
        content: '{\n  "results": 14\n}',
        model: "openai/gpt-4.1-nano",
        created: "2025-04-19T14:50:44Z",
        annotations: [
          {
            reward: 1,
            by: "guest-rater",
            at: "2025-04-19T14:50:48Z",
          },
          {
            reward: 1,
            by: "guest-rater",
            at: "2025-04-19T14:50:49Z",
          },
        ],
        is_json: true,
        obeys_schema: false,
      },
      {
        id: "alt-3",
        content: '{\n  "result": 14\n}',
        model: "openai/gpt-4.1-nano",
        created: "2025-04-19T14:50:44Z",
        annotations: [
          {
            reward: 1,
            by: "guest-rater",
            at: "2025-04-19T14:50:48Z",
          },
          {
            reward: 1,
            by: "guest-rater",
            at: "2025-04-19T14:50:49Z",
          },
        ],
        is_json: true,
        obeys_schema: true,
      },
    ],
  },
  "a1b2c3d4-5e6f-7g8h-9i0j-klmno1p2q3r4": {
    id: "a1b2c3d4-5e6f-7g8h-9i0j-klmno1p2q3r4",
    name: "Multi-turn conversation",
    pairNumber: 3,
    request: {
      id: "a1b2c3d4-5e6f-7g8h-9i0j-klmno1p2q3r4",
      request_log_id: "e5f6g7h8-i9j0-k1l2-m3n4-o5p6q7r8s9t0",
      intercept_key: "sk-intercept-v1-KJteRu50CwsmoPE5pnwz1MZJqzCOw9u5rwNEP1iM4iTzDHx3lzIx",
      messages: [
        {
          role: "system",
          content: "You are a helpful assistant",
        },
        {
          role: "user",
          content: "What is 2+12?",
        },
        {
          role: "assistant",
          content: "It is 14.",
        },
        {
          role: "user",
          content: "What is the double of that?",
        },
      ],
      model: "openai/gpt-4.1-nano",
      response_format: null,
      request_timestamp: "2025-04-18T15:30:22.123456Z",
    },
    mainResponse: {
      id: "gen-1745061764-62VpUnIe6ZchnN9UNLM",
      content: "The double of 14 is 28.",
      model: "openai/gpt-4.1-nano",
      created: "2025-04-18T15:30:25Z",
      annotations: [],
      metadata: {
        completion_id: "a1b2c3d4-5e6f-7g8h-9i0j-klmno1p2q3r4",
        annotation_target_id: "4c651f6d-0gc1-520d-0840-9217gf1e120d",
        provider: "OpenAI",
        model: "openai/gpt-4.1-nano",
        prompt_tokens: 32,
        completion_tokens: 7,
        total_tokens: 39,
        choice_finish_reason: "stop",
        choice_role: "assistant",
        choice_content: "The double of 14 is 28.",
      },
      is_json: false,
      obeys_schema: null,
    },
    alternativeResponses: [],
  },
}

// Status indicator component
function StatusIndicator({ status }: { status: "complete" | "partial" | "none" }) {
  let bgColor = ""
  let title = ""

  switch (status) {
    case "complete":
      bgColor = "bg-green-500"
      title = "Complete"
      break
    case "partial":
      bgColor = "bg-amber-400"
      title = "Partial"
      break
    case "none":
      bgColor = "bg-gray-300"
      title = "None"
      break
  }

  return (
    <div className="flex justify-center">
      <div className={`w-3 h-3 rounded-full ${bgColor}`} title={title} aria-label={`${title} status`}></div>
    </div>
  )
}

export function RequestsOverviewV2() {
  const [requests] = useState(mockRequests)
  const [expandedRequestId, setExpandedRequestId] = useState<string | null>(null)
  const [showAlternatives, setShowAlternatives] = useState(true)
  const [newAlternative, setNewAlternative] = useState("")

  const toggleRequestExpansion = (id: string) => {
    setExpandedRequestId(expandedRequestId === id ? null : id)
  }

  return (
    <div className="rounded-md border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-[50px]"></TableHead>
            <TableHead className="w-[100px]">ID</TableHead>
            <TableHead className="w-[200px]">Name</TableHead>
            <TableHead>Question</TableHead>
            <TableHead className="w-[150px]">Responses</TableHead>
            <TableHead className="w-[60px] text-center">
              <div className="flex items-center justify-center gap-1">
                SFT
                <InfoModal
                  title="Supervised Fine-Tuning (SFT)"
                  description="SFT means you have to reward one of the responses to the request with reward 1. If the model's response is not good you can create an alternative and annotate that with reward 1."
                  triggerClassName="ml-1"
                />
              </div>
            </TableHead>
            <TableHead className="w-[60px] text-center">
              <div className="flex items-center justify-center gap-1">
                DPO
                <InfoModal
                  title="Direct Preference Optimization (DPO)"
                  description="DPO means you have to have one response with reward 1 and one response with reward 0. They will form a preference pair. To make a good preference pair make the response with reward 1 be very good and the one with reward 0 be reasonable but not as you want."
                  triggerClassName="ml-1"
                />
              </div>
            </TableHead>
            <TableHead className="w-[120px]">Date</TableHead>
            <TableHead className="w-[50px]"></TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {requests.map((request) => (
            <>
              <TableRow key={request.id} className="h-12 hover:bg-gray-50">
                <TableCell>
                  <button
                    onClick={() => toggleRequestExpansion(request.id)}
                    className="p-1 rounded-md hover:bg-gray-200"
                  >
                    {expandedRequestId === request.id ? (
                      <ChevronDown className="h-5 w-5 text-gray-500" />
                    ) : (
                      <ChevronRight className="h-5 w-5 text-gray-500" />
                    )}
                  </button>
                </TableCell>
                <TableCell className="font-mono text-xs text-gray-500">{request.id.substring(0, 8)}...</TableCell>
                <TableCell className="font-medium">{request.name}</TableCell>
                <TableCell className="truncate max-w-[400px]">{request.question}</TableCell>
                <TableCell>
                  <Badge variant="outline" className="bg-gray-50">
                    {request.annotatedResponses}/{request.totalResponses}
                  </Badge>
                </TableCell>
                <TableCell>
                  <StatusIndicator status={request.sftStatus} />
                </TableCell>
                <TableCell>
                  <StatusIndicator status={request.dpoStatus} />
                </TableCell>
                <TableCell className="text-gray-500 text-sm">
                  {new Date(request.timestamp).toLocaleDateString()}
                </TableCell>
                <TableCell>
                  <Link href={`/requests/${request.id}`} className="block p-1 rounded-md hover:bg-gray-200">
                    <ArrowRight className="h-5 w-5 text-gray-400" />
                  </Link>
                </TableCell>
              </TableRow>
              {expandedRequestId === request.id && mockRequestDetails[request.id] && (
                <TableRow>
                  <TableCell colSpan={9} className="p-0 border-t-0">
                    <div className="p-6 bg-gray-50">
                      <div className="space-y-6">
                        <div className="mb-6">
                          <h3 className="font-medium mb-2">Request:</h3>
                          <RequestCard request={mockRequestDetails[request.id].request} />
                        </div>

                        <div className="mb-6">
                          <h3 className="font-medium mb-2">Response:</h3>
                          <ResponseSection response={mockRequestDetails[request.id].mainResponse} />
                        </div>

                        <div className="mb-6">
                          <AlternativesSection
                            alternatives={mockRequestDetails[request.id].alternativeResponses}
                            showAlternatives={showAlternatives}
                            setShowAlternatives={setShowAlternatives}
                          />
                        </div>

                        <NewAlternativeForm newAlternative={newAlternative} setNewAlternative={setNewAlternative} />
                      </div>
                    </div>
                  </TableCell>
                </TableRow>
              )}
            </>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}
