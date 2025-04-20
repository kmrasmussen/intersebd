import { useParams } from 'react-router-dom';
import { RequestDetails } from "@/components/request-details";

// Define the expected shape of the URL parameters
interface RequestDetailsParams {
  projectId: string;
  requestId: string;
  [key: string]: string | undefined; // Allow other potential params
}

export default function RequestDetailsPage() {
  // Use the useParams hook to get the dynamic segments from the URL
  // The keys (projectId, requestId) must match the route definition in App.tsx
  const { projectId, requestId } = useParams<RequestDetailsParams>();
  console.log("Project ID:", projectId);
  // Check if requestId exists before rendering RequestDetails
  if (!requestId) {
    // Handle the case where requestId is missing, e.g., show an error or redirect
    return <div>Error: Request ID not found in URL.</div>;
  }

  // Optionally use projectId if RequestDetails needs it
  // console.log("Project ID:", projectId);

  return (
    <div className="container mx-auto py-4">
      {/* Pass the extracted requestId to the RequestDetails component */}
      <RequestDetails id={requestId} />
    </div>
  );
}