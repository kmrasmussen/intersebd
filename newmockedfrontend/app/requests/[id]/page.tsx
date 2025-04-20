import { RequestDetails } from "@/components/request-details"

// Function to get the list of IDs to pre-render
// Replace this with your actual logic
async function getRequestIdsForStaticGeneration() {
  // --- IMPORTANT ---
  // You MUST provide the actual list of IDs here.
  // This could be from an API call (if accessible at build time),
  // reading a file, or a hardcoded list if they are known.
  // If the IDs are purely dynamic and unknown at build time,
  // static export might not work for this route without changes.
  //
  // Example hardcoded list:
  return [
    { id: 'some-known-id-1' },
    { id: 'some-known-id-2' },
    // Add all IDs you want to pre-render
  ]

  // Example fetching (if possible during build):
  // try {
  //   const res = await fetch('https://your-api.com/requests/ids'); // Ensure this endpoint exists and is reachable by the build server
  //   const ids = await res.json(); // Assuming it returns [{ id: '...' }, ...]
  //   return ids;
  // } catch (error) {
  //   console.error("Failed to fetch request IDs for static generation:", error);
  //   return []; // Return empty array on error to avoid build failure, or handle differently
  // }
}

// Add this function to define static paths
export async function generateStaticParams() {
  const paths = await getRequestIdsForStaticGeneration();
  return paths;
}

export default function RequestDetailsPage({ params }: { params: { id: string } }) {
  return (
    <div className="container mx-auto py-4">
      <RequestDetails id={params.id} />
    </div>
  )
}
