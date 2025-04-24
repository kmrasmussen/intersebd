// filepath: /home/kasper/randomrepos/intersebd/newmockedfrontend/src/pages/GenerateDatasetPage.tsx
import { DownloadDatasetComponent } from "@/components/download-dataset-component";
import { useParams } from "react-router-dom"; // Import useParams
import LoadingSpinner from "@/components/LoadingSpinner"; // Optional: for loading state

export default function GenerateDatasetPage() {
  // Get projectId from URL parameters
  const { projectId } = useParams<{ projectId: string }>();

  // Optional: Handle case where projectId might be undefined initially or if the route is wrong
  if (!projectId) {
    // You could show a loading state or an error message
    console.error("GenerateDatasetPage: Project ID not found in URL parameters.");
    return <LoadingSpinner />; // Or return an error component
  }

  return (
    <div className="container mx-auto py-4">
      <h1 className="text-2xl font-bold mb-6">Generate Dataset</h1>
      <div className="max-w-2xl">
        {/* Pass the dynamic projectId from useParams */}
        <DownloadDatasetComponent
          dpoAnnotatedResponses={3} // Keep DPO mocked for now
          requiredResponses={20}
          projectId={projectId} // Pass the projectId from the URL
        />
      </div>
    </div>
  );
}