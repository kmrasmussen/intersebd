import { useParams } from 'react-router-dom';
import { RequestDetails } from "@/components/request-details"; // Assuming this path is correct

// Define the expected shape of the URL parameters
interface RequestDetailsParams {
  projectId: string;
  requestId: string;
  [key: string]: string | undefined; // Allow other potential params
}

export default function RequestDetailsPage() {
  const { projectId, requestId } = useParams<RequestDetailsParams>();

  // Add checks for both projectId and requestId
  if (!projectId || !requestId) {
    // Handle the case where either ID is missing
    return <div>Error: Project ID or Request ID not found in URL.</div>;
  }

  console.log("RequestDetailsPage - Project ID:", projectId, "Request ID:", requestId);

  return (
    <div className="container mx-auto py-4">
      {/* Pass both projectId and requestId to the RequestDetails component */}
      <RequestDetails projectId={projectId} requestId={requestId} />
    </div>
  );
}