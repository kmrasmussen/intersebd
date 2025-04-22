import { useState, useEffect } from 'react';

// --- Define Types (Copy or import from a shared types file) ---
//type RequestStatus = "complete" | "partial" | "none";

interface Message {
  role: string;
  content: string;
}

interface Annotation {
  reward: number;
  by: string;
  at: string; // ISO 8601 format
}

interface ResponseDetail {
  id: string;
  content: string;
  model: string;
  created: string; // ISO 8601 format
  annotations: Annotation[];
  metadata?: Record<string, any> | null;
  is_json: boolean;
  obeys_schema?: boolean | null;
}

interface RequestDetailData {
  id: string;
  project_id: string;
  messages: Message[];
  model: string;
  response_format?: Record<string, any> | null;
  request_timestamp: string; // ISO 8601 format
}

interface MockRequestDetail {
  id: string;
  name: string;
  pairNumber: number; // This seems mocked, adjust if needed
  request: RequestDetailData;
  mainResponse: ResponseDetail;
  alternativeResponses: ResponseDetail[];
}
// --- End Define Types ---

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";
const GUEST_USER_ID_HEADER = "X-Guest-User-Id";

interface RequestDetailsProps {
  projectId: string;
  requestId: string;
}

export function RequestDetails({ projectId, requestId }: RequestDetailsProps) {
  const [details, setDetails] = useState<MockRequestDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchDetails = async () => {
      if (!projectId || !requestId) {
        setError("Project ID or Request ID is missing.");
        setIsLoading(false);
        return;
      }

      setIsLoading(true);
      setError(null);
      setDetails(null); // Clear previous details

      const apiUrl = `${API_BASE_URL}/mock-next/${projectId}/requests/${requestId}`;
      const guestUserId = localStorage.getItem('guestUserId');
      const headers: HeadersInit = {};
      if (guestUserId) {
        headers[GUEST_USER_ID_HEADER] = guestUserId;
      }

      console.log(`RequestDetails: Fetching from ${apiUrl}`);
      try {
        const response = await fetch(apiUrl, { headers });

        if (!response.ok) {
          let errorDetail = `HTTP error! status: ${response.status}`;
          try {
            const errorData = await response.json();
            errorDetail += ` - ${errorData.detail || 'Unknown error'}`;
          } catch (jsonError) {
            // Ignore if response is not JSON
          }
          throw new Error(errorDetail);
        }

        const data: MockRequestDetail = await response.json();
        setDetails(data);
        console.log("RequestDetails: Fetched data:", data);

      } catch (err: any) {
        console.error("RequestDetails: Failed to fetch details:", err);
        setError(err.message || "An unknown error occurred");
      } finally {
        setIsLoading(false);
      }
    };

    fetchDetails();
  }, [projectId, requestId]); // Re-fetch if projectId or requestId changes

  if (isLoading) {
    return <div>Loading request details...</div>;
  }

  if (error) {
    return <div className="text-red-500">Error loading details: {error}</div>;
  }

  if (!details) {
    return <div>No details found for this request.</div>;
  }

  // --- Render the Fetched Data ---
  return (
    <div>
      <h1 className="text-2xl font-bold mb-4">{details.name} (ID: {details.id})</h1>

      <div className="mb-6 p-4 border rounded bg-gray-50">
        <h2 className="text-xl font-semibold mb-2">Request</h2>
        <p><strong>Model:</strong> {details.request.model}</p>
        <p><strong>Timestamp:</strong> {details.request.request_timestamp}</p>
        {details.request.response_format && (
          <p><strong>Response Format:</strong> <pre className="text-xs bg-gray-200 p-1 rounded overflow-x-auto">{JSON.stringify(details.request.response_format, null, 2)}</pre></p>
        )}
        <h3 className="text-lg font-medium mt-2 mb-1">Messages:</h3>
        {details.request.messages.map((msg, index) => (
          <div key={index} className={`p-2 my-1 rounded ${msg.role === 'user' ? 'bg-blue-100' : 'bg-green-100'}`}>
            <strong>{msg.role}:</strong>
            <pre className="whitespace-pre-wrap text-sm overflow-x-auto">{msg.content}</pre>
          </div>
        ))}
      </div>

      <div className="mb-6 p-4 border rounded bg-white">
        <h2 className="text-xl font-semibold mb-2">Main Response</h2>
        <p><strong>ID:</strong> {details.mainResponse.id}</p>
        <p><strong>Created:</strong> {details.mainResponse.created}</p>
        <p><strong>Is JSON:</strong> {details.mainResponse.is_json ? 'Yes' : 'No'}</p>
        <h3 className="text-lg font-medium mt-2 mb-1">Content:</h3>
        <pre className="whitespace-pre-wrap p-2 border rounded bg-gray-50 text-sm overflow-x-auto">{details.mainResponse.content}</pre>
        {/* TODO: Render Annotations */}
      </div>

      {details.alternativeResponses.length > 0 && (
        <div className="p-4 border rounded bg-gray-100">
          <h2 className="text-xl font-semibold mb-2">Alternative Responses ({details.alternativeResponses.length})</h2>
          {details.alternativeResponses.map((alt, index) => (
            <div key={alt.id || index} className="mb-4 p-3 border rounded bg-white">
              <p><strong>ID:</strong> {alt.id}</p>
              <p><strong>Created:</strong> {alt.created}</p>
              <p><strong>Is JSON:</strong> {alt.is_json ? 'Yes' : 'No'}</p>
              <h4 className="text-md font-medium mt-1 mb-1">Content:</h4>
              <pre className="whitespace-pre-wrap p-2 border rounded bg-gray-50 text-sm overflow-x-auto">{alt.content}</pre>
              {/* TODO: Render Annotations */}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}