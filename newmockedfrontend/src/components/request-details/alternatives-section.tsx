"use client"

import { Button } from "@/components/ui/button";
import { ResponseCard } from "@/components/response-card";

// Ensure Response type includes annotation_target_id
type Response = {
  id: string;
  annotation_target_id?: string | null; // <-- Ensure this is present
  content: string;
  model: string;
  created: string;
  annotations: Array<{
    reward: number;
    by: string; // Consider if this should be Optional<string> or Optional<uuid.UUID>
    at: string;
  }>;
  metadata?: Record<string, any>;
  is_json: boolean;
  obeys_schema: boolean | null;
};

// Add projectId to props
type AlternativesSectionProps = {
  alternatives: Response[];
  showAlternatives: boolean;
  setShowAlternatives: (show: boolean) => void;
  projectId: string; // <-- ADD projectId prop type
};

// Update function signature to accept projectId
export function AlternativesSection({
  alternatives,
  showAlternatives,
  setShowAlternatives,
  projectId, // <-- ACCEPT projectId prop
}: AlternativesSectionProps) {
  return (
    <>
      <div className="flex items-center justify-between mb-2">
        <h3 className="font-medium">Alternatives:</h3>
        <Button variant="outline" size="sm" onClick={() => setShowAlternatives(!showAlternatives)}>
          {showAlternatives ? "Hide Alternatives" : "Show/Refresh Alternatives"}
        </Button>
      </div>

      {showAlternatives && alternatives.length > 0 && (
        <div className="space-y-4">
          {alternatives.map((response, index) => (
            // Pass projectId down to ResponseCard
            <ResponseCard
              key={response.id || index} // Use response.id if available and unique
              response={response}
              isAlternative
              projectId={projectId} // <-- PASS projectId here
            />
          ))}
        </div>
      )}

      {showAlternatives && alternatives.length === 0 && (
        <div className="p-4 bg-gray-50 rounded-md text-gray-500 italic text-center">
          No alternative responses available.
        </div>
      )}
    </>
  );
}
