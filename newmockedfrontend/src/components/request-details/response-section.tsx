import { ResponseCard } from "@/components/response-card"; // Corrected path

type Response = {
  id: string;
  annotation_target_id?: string | null; // Ensure this is present
  content: string;
  model: string;
  created: string;
  annotations: Array<{
    reward: number;
    by: string;
    at: string;
  }>;
  metadata?: Record<string, any>;
  is_json: boolean;
  obeys_schema: boolean | null;
};

// Add projectId to props interface
interface ResponseSectionProps {
  response: Response;
  projectId: string; // <-- Add projectId prop
}

// Update function signature to accept projectId
export function ResponseSection({ response, projectId }: ResponseSectionProps) {
  // Pass projectId down to ResponseCard
  return <ResponseCard response={response} projectId={projectId} />;
}
