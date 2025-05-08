"use client"

import { Button } from "@/components/ui/button";
import { ResponseCard } from "@/components/response-card";
import { RJSFSchema } from "@rjsf/utils"; // <-- Import type

// Define/Import Response and Annotation types
type Annotation = { id: string; reward: number; by: string; at: string; };
type Response = {
  id: string;
  annotation_target_id?: string | null;
  content: string;
  model: string;
  created: string;
  annotations: Annotation[];
  metadata?: Record<string, any>;
  is_json: boolean;
  obeys_schema: boolean | null;
};

type AlternativesSectionProps = {
  alternatives: Response[];
  showAlternatives: boolean;
  setShowAlternatives: (show: boolean) => void;
  projectId: string;
  onAnnotationAdded: (targetId: string, newAnnotationData: any) => void;
  onResponseDeleted: (targetId: string) => void;
  onAnnotationDeleted: (targetId: string, annotationId: string) => void;
  activeSchema: RJSFSchema | null; // <-- Add prop
};

export function AlternativesSection({
  alternatives,
  showAlternatives,
  setShowAlternatives,
  projectId,
  onAnnotationAdded,
  onResponseDeleted,
  onAnnotationDeleted,
  activeSchema, // <-- Destructure prop
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
            <ResponseCard
              key={response.id || index}
              response={response}
              isAlternative
              projectId={projectId}
              onAnnotationAdded={onAnnotationAdded}
              onResponseDeleted={onResponseDeleted}
              onAnnotationDeleted={onAnnotationDeleted}
              activeSchema={activeSchema} // <-- Pass down
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
