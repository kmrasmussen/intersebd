"use client"

import { useState, useEffect, useCallback } from "react"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "./ui/table"
import { Badge } from "./ui/badge"
import { ChevronDown, ChevronRight, ArrowRight, RefreshCw } from "lucide-react"
import { RequestCard } from "./request-details/request-card"
import { ResponseSection } from "./request-details/response-section"
import { AlternativesSection } from "./request-details/alternatives-section"
import { NewAlternativeForm } from "./request-details/new-alternative-form"
import { Link } from "react-router-dom"
import { InfoModal } from "./info-modal"
import { RJSFSchema } from "@rjsf/utils"

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
interface Annotation {
  id: string;
  reward: number;
  by: string;
  at: string;
}

interface ResponseDetail {
  id: string;
  annotation_target_id?: string | null;
  content: string;
  model: string;
  created: string;
  annotations: Annotation[];
  metadata?: Record<string, any>;
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
  mainResponse?: ResponseDetail;
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

export function RequestsOverviewV2({ projectId, refreshTrigger }: { projectId: string; refreshTrigger: number }) {
  const [requests, setRequests] = useState<MockRequest[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [expandedRequestId, setExpandedRequestId] = useState<string | null>(null)
  const [currentDetails, setCurrentDetails] = useState<MockRequestDetail | null>(null)
  const [isLoadingDetails, setIsLoadingDetails] = useState(false)
  const [detailsError, setDetailsError] = useState<string | null>(null)

  const [showAlternatives, setShowAlternatives] = useState(true)
  const [activeSchema, setActiveSchema] = useState<RJSFSchema | null>(null)
  const [isLoadingSchema, setIsLoadingSchema] = useState(false)

  console.log(isLoadingSchema, "isLoadingSchema")

  const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || ""
  const GUEST_USER_ID_HEADER = "X-Guest-User-Id"

  useEffect(() => {
    const fetchRequests = async () => {
      if (!projectId) {
        setError("Project ID is missing.");
        setIsLoading(false);
        return;
      }
      setIsLoading(true);
      setError(null);
      setRequests([]);

      const guestUserId = localStorage.getItem('guestUserId');
      const headers: HeadersInit = {};
      if (guestUserId) {
        headers[GUEST_USER_ID_HEADER] = guestUserId;
      }
      const url = `${API_BASE_URL}/mock-next/${projectId}/requests-summary`;

      try {
        const response = await fetch(url, { headers });
        if (!response.ok) {
          let errorDetail = `Failed to fetch requests: ${response.status}`;
          try { const errorData = await response.json(); errorDetail += ` - ${errorData.detail || 'Unknown error'}`; } catch { }
          throw new Error(errorDetail);
        }
        const data: MockRequest[] = await response.json();
        setRequests(data);
      } catch (err: any) {
        setError(err.message || "An unknown error occurred while fetching requests.");
        setRequests([]);
      } finally {
        setIsLoading(false);
      }
    };

    fetchRequests();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId, API_BASE_URL, GUEST_USER_ID_HEADER, refreshTrigger]);

  const fetchRequestDetailsAndSchema = useCallback(async (reqId: string) => {
    if (!projectId) return

    console.log(`Fetching details for request ${reqId} and active schema for project ${projectId}`)
    setIsLoadingDetails(true)
    setIsLoadingSchema(true)
    setDetailsError(null)
    setCurrentDetails(null)
    setActiveSchema(null)

    const guestUserId = localStorage.getItem('guestUserId')
    const headers: HeadersInit = {}
    if (guestUserId) {
      headers[GUEST_USER_ID_HEADER] = guestUserId
    }

    const detailsUrl = `${API_BASE_URL}/mock-next/${projectId}/requests/${reqId}`
    const schemaUrl = `${API_BASE_URL}/mock-next/${projectId}/schemas/current`

    try {
      const [detailsResponse, schemaResponse] = await Promise.all([
        fetch(detailsUrl, { headers }),
        fetch(schemaUrl, { headers })
      ])

      if (!detailsResponse.ok) {
        let errorDetail = `Details fetch failed: ${detailsResponse.status}`
        try { const errorData = await detailsResponse.json(); errorDetail += ` - ${errorData.detail || 'Unknown error'}`; } catch { }
        throw new Error(errorDetail)
      }
      const detailsData: MockRequestDetail = await detailsResponse.json()
      setCurrentDetails(detailsData)
      console.log("Details fetched successfully:", detailsData)

      if (schemaResponse.ok) {
        const schemaData = await schemaResponse.json()
        if (schemaData && schemaData.schema_content) {
          setActiveSchema(schemaData.schema_content as RJSFSchema)
          console.log("Active schema fetched successfully:", schemaData.schema_content)
        } else {
          console.log("Schema endpoint returned OK, but no schema_content found.")
          setActiveSchema(null)
        }
      } else if (schemaResponse.status === 404) {
        console.log("No active schema found for project (404).")
        setActiveSchema(null)
      } else {
        console.error(`Schema fetch failed: ${schemaResponse.status}`)
        setActiveSchema(null)
      }

    } catch (error: any) {
      console.error("Failed to fetch request details or schema:", error)
      setDetailsError(error.message || "Failed to load details or schema")
      setCurrentDetails(null)
      setActiveSchema(null)
    } finally {
      setIsLoadingDetails(false)
      setIsLoadingSchema(false)
    }
  }, [projectId, API_BASE_URL, GUEST_USER_ID_HEADER])

  useEffect(() => {
    if (expandedRequestId) {
      fetchRequestDetailsAndSchema(expandedRequestId)
    } else {
      setCurrentDetails(null)
      setActiveSchema(null)
    }
  }, [expandedRequestId, fetchRequestDetailsAndSchema])

  const toggleRequestExpansion = (id: string) => {
    setExpandedRequestId(expandedRequestId === id ? null : id)
  }

  const handleAnnotationAdded = (targetId: string, newAnnotationData: any) => {
    console.log("requests-overview-v2: handleAnnotationAdded", targetId, newAnnotationData)
    setCurrentDetails(prevDetails => {
      if (!prevDetails) return null
      const updateAnnotations = (response: ResponseDetail | undefined): ResponseDetail | undefined => {
        if (!response || response.annotation_target_id !== targetId) return response
        return {
          ...response,
          annotations: [...response.annotations, newAnnotationData]
        }
      }
      return {
        ...prevDetails,
        mainResponse: updateAnnotations(prevDetails.mainResponse) as ResponseDetail,
        alternativeResponses: prevDetails.alternativeResponses.map(alt => updateAnnotations(alt) || alt)
      }
    })
  }

  const handleAnnotationDeleted = (targetId: string, annotationId: string) => {
    console.log("requests-overview-v2: handleAnnotationDeleted", targetId, annotationId)
    setCurrentDetails(prevDetails => {
      if (!prevDetails) return null
      const updateAnnotations = (response: ResponseDetail | undefined): ResponseDetail | undefined => {
        if (!response || response.annotation_target_id !== targetId) return response
        return {
          ...response,
          annotations: response.annotations.filter(ann => ann.id !== annotationId)
        }
      }
      return {
        ...prevDetails,
        mainResponse: updateAnnotations(prevDetails.mainResponse) as ResponseDetail,
        alternativeResponses: prevDetails.alternativeResponses.map(alt => updateAnnotations(alt) || alt)
      }
    })
  }

  const handleResponseDeleted = (targetId: string) => {
    console.log("requests-overview-v2: handleResponseDeleted", targetId)
    setCurrentDetails(prevDetails => {
      if (!prevDetails) return null
      if (prevDetails.mainResponse?.annotation_target_id === targetId) {
        console.warn("Main response deleted - UI update needed.")
        return { ...prevDetails, mainResponse: undefined }
      }
      return {
        ...prevDetails,
        alternativeResponses: prevDetails.alternativeResponses.filter(alt => alt.annotation_target_id !== targetId)
      }
    })
  }

  const handleAlternativeAdded = (newAlternative: ResponseDetail) => {
    console.log("requests-overview-v2: handleAlternativeAdded", newAlternative)
    setCurrentDetails(prevDetails => {
      if (!prevDetails) return null
      return {
        ...prevDetails,
        alternativeResponses: [...prevDetails.alternativeResponses, newAlternative]
      }
    })
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
                        <div className="text-center p-4"><RefreshCw className="h-6 w-6 animate-spin inline-block" /> Loading details...</div>
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
                            {currentDetails.mainResponse ? (
                              <ResponseSection
                                response={currentDetails.mainResponse}
                                projectId={projectId}
                                onAnnotationAdded={handleAnnotationAdded}
                                onResponseDeleted={handleResponseDeleted}
                                onAnnotationDeleted={handleAnnotationDeleted}
                                activeSchema={activeSchema}
                              />
                            ) : (
                              <div className="p-4 bg-yellow-50 rounded-md text-yellow-700 italic text-center">
                                Main response is missing or was deleted.
                              </div>
                            )}
                          </div>

                          <div className="mb-6">
                            <AlternativesSection
                              alternatives={currentDetails.alternativeResponses}
                              showAlternatives={showAlternatives}
                              setShowAlternatives={setShowAlternatives}
                              projectId={projectId}
                              onAnnotationAdded={handleAnnotationAdded}
                              onResponseDeleted={handleResponseDeleted}
                              onAnnotationDeleted={handleAnnotationDeleted}
                              activeSchema={activeSchema}
                            />
                          </div>

                          <NewAlternativeForm
                            projectId={projectId}
                            requestId={currentDetails.id}
                            onAlternativeAdded={handleAlternativeAdded}
                          />
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
