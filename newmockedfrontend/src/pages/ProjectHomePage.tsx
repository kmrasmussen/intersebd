import { useParams } from "react-router-dom"; // Import useParams
import { RequestsOverviewV2 } from "@/components/requests-overview-v2";
import { PageTabs } from "@/components/page-tabs"; // Assuming page-tabs is moved/created in components

// Remove generateStaticParams function

// Remove params from function signature
export default function ProjectHomePage() {
  // Get projectId from URL using useParams hook
  const { projectId } = useParams<{ projectId: string }>();

  // Handle case where projectId might be undefined (optional, but good practice)
  if (!projectId) {
    // You could redirect or show an error/loading state
    return <div>Loading project or project ID missing...</div>;
  }

  console.log("Project ID:", projectId);

  return (
    <div className="container mx-auto py-4">
      <h1 className="text-2xl font-bold mb-6">Requests Overview (Project: {projectId})</h1>
      {/* Pass projectId down */}
      <PageTabs projectId={projectId} />
      <RequestsOverviewV2 projectId={projectId} />
    </div>
  );
}