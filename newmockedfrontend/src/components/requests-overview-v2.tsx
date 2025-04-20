"use client"

import { useState, useEffect } from "react"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "./ui/table"
import { Badge } from "./ui/badge"
import { ChevronDown, ChevronRight, ArrowRight } from "lucide-react"
import { RequestCard } from "./request-details/request-card"
import { ResponseSection } from "./request-details/response-section"
import { AlternativesSection } from "./request-details/alternatives-section"
import { NewAlternativeForm } from "./request-details/new-alternative-form"
import { Link } from "react-router-dom"
import { InfoModal } from "./info-modal"

// --- Define Types ---
type RequestStatus = "complete" | "partial" | "none";

interface MockRequest {
  id: string;
  name: string;
  question: string;
  totalResponses: number;
  annotatedResponses: number;
  timestamp: string;
  sftStatus: RequestStatus;
  dpoStatus: RequestStatus;
}

interface Message { role: string; content: string; }
interface Annotation { reward: number; by: string; at: string; }

interface ResponseDetail {
  id: string;
  content: string;
  model: string;
  created: string;
  annotations: Annotation[];
  metadata?: any;
  is_json: boolean;
  obeys_schema: boolean | null;
}
interface RequestDetailData {
  id: string;
  request_log_id: string;
  intercept_key: string;
  messages: Message[];
  model: string;
  response_format: null;
  request_timestamp: string;
}

interface MockRequestDetail {
  id: string;
  name: string;
  pairNumber: number;
  request: RequestDetailData;
  mainResponse: ResponseDetail;
  alternativeResponses: ResponseDetail[];
}
// --- End Define Types ---

function StatusIndicator({ status }: { status: RequestStatus }) {
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

export function RequestsOverviewV2({ projectId }: { projectId: string }) {
  const [requests, setRequests] = useState<MockRequest[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [expandedRequestId, setExpandedRequestId] = useState<string | null>(null)
  const [currentDetails, setCurrentDetails] = useState<MockRequestDetail | null>(null)
  const [isLoadingDetails, setIsLoadingDetails] = useState(false)
  const [detailsError, setDetailsError] = useState<string | null>(null)

  const [showAlternatives, setShowAlternatives] = useState(true)
  const [newAlternative, setNewAlternative] = useState("")

  useEffect(() => {
    const fetchRequests = async () => {
      setIsLoading(true)
      setError(null)
      try {
        // Use environment variable for the base URL
        const baseUrl = import.meta.env.VITE_API_BASE_URL;
        const apiUrl = `${baseUrl}/mock-next/${projectId}/requests-summary`
        console.log("Fetching from:", apiUrl)

        const response = await fetch(apiUrl)
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`)
        }
        const data: MockRequest[] = await response.json()
        console.log("data from overview", data)
        setRequests(data)
      } catch (e: any) {
        console.error("Failed to fetch requests:", e)
        setError(e.message || "Failed to fetch data")
      } finally {
        setIsLoading(false)
      }
    }

    if (projectId) {
      fetchRequests()
    }
  }, [projectId])

  useEffect(() => {
    const fetchRequestDetails = async (id: string) => {
      setIsLoadingDetails(true)
      setDetailsError(null)
      setCurrentDetails(null)
      try {
        // Use environment variable for the base URL
        const baseUrl = import.meta.env.VITE_API_BASE_URL;
        const apiUrl = `${baseUrl}/mock-next/${projectId}/requests/${id}`
        console.log("Fetching details from:", apiUrl)
        const response = await fetch(apiUrl)
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`)
        }
        const data: MockRequestDetail = await response.json()
        console.log("data", data)
        console.log('data for a specific request', data)
        setCurrentDetails(data)
      } catch (e: any) {
        console.error("Failed to fetch request details:", e)
        setDetailsError(e.message || "Failed to fetch details")
      } finally {
        setIsLoadingDetails(false)
      }
    }

    if (expandedRequestId) {
      fetchRequestDetails(expandedRequestId)
    }
  }, [expandedRequestId, projectId])

  const toggleRequestExpansion = (id: string) => {
    setExpandedRequestId(expandedRequestId === id ? null : id)
  }

  if (isLoading) {
    return <div className="p-4">Loading requests...</div>
  }
  if (error) {
    return <div className="p-4 text-red-600">Error loading requests: {error}</div>
  }
  if (requests.length === 0) {
    return <div className="p-4">No requests found for this project.</div>
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
                  <Link to={`/${projectId}/requests/${request.id}`} className="block p-1 rounded-md hover:bg-gray-200">
                    <ArrowRight className="h-5 w-5 text-gray-400" />
                  </Link>
                </TableCell>
              </TableRow>
              {expandedRequestId === request.id && (
                <TableRow>
                  <TableCell colSpan={9} className="p-0 border-t-0">
                    <div className="p-6 bg-gray-50">
                      {isLoadingDetails ? (
                        <div>Loading details...</div>
                      ) : detailsError ? (
                        <div className="text-red-600">Error loading details: {detailsError}</div>
                      ) : currentDetails ? (
                        <div className="space-y-6">
                          <div className="mb-6">
                            <h3 className="font-medium mb-2">Request:</h3>
                            <RequestCard request={currentDetails.request} />
                          </div>

                          <div className="mb-6">
                            <h3 className="font-medium mb-2">Response:</h3>
                            <ResponseSection response={currentDetails.mainResponse} />
                          </div>

                          <div className="mb-6">
                            <AlternativesSection
                              alternatives={currentDetails.alternativeResponses}
                              showAlternatives={showAlternatives}
                              setShowAlternatives={setShowAlternatives}
                            />
                          </div>

                          <NewAlternativeForm newAlternative={newAlternative} setNewAlternative={setNewAlternative} />
                        </div>
                      ) : (
                        <div>No details available.</div>
                      )}
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
