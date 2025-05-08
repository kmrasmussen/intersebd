import { useState } from 'react'; // <-- Import useState
import { useParams } from "react-router-dom";
import { RequestsOverviewV2 } from "@/components/requests-overview-v2";
import { PageTabs } from "@/components/page-tabs";
// Assuming CodeExample is NOT directly imported/used here, but inside PageTabs

export default function ProjectHomePage() {
  const { projectId } = useParams<{ projectId: string }>();
  const [refreshKey, setRefreshKey] = useState(0); // <-- Add state for refresh trigger

  if (!projectId) {
    return <div>Loading project or project ID missing...</div>;
  }

  console.log("Project ID:", projectId);

  // --- Add the callback function ---
  // This function will be passed down to CodeExample via PageTabs
  const handleApiCallSuccess = () => {
    console.log(`[ProjectHomePage] handleApiCallSuccess called. Updating refresh key from ${refreshKey} to ${refreshKey + 1}`);
    setRefreshKey(prevKey => prevKey + 1);
  };
  // --- End callback function ---

  return (
    <div className="container mx-auto py-4">
      <h1 className="text-2xl font-bold mb-6">Requests Overview (Project: {projectId})</h1>

      {/* Pass projectId AND the callback down to PageTabs */}
      <PageTabs
        projectId={projectId}
        onApiCallSuccess={handleApiCallSuccess} // <-- Pass callback down
      />

      {/* Pass projectId and refreshTrigger down to RequestsOverviewV2 */}
      <RequestsOverviewV2
        projectId={projectId}
        refreshTrigger={refreshKey} // <-- Pass state down
      />
    </div>
  );
}