import { ResponseCard } from "@/components/response-card";
import { RJSFSchema } from "@rjsf/utils";

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

interface ResponseSectionProps {
  response: Response;
  projectId: string;
  onAnnotationAdded: (targetId: string, newAnnotationData: any) => void;
  onResponseDeleted?: (targetId: string) => void;
  onAnnotationDeleted: (targetId: string, annotationId: string) => void;
  activeSchema: RJSFSchema | null;
}

export function ResponseSection({ response, projectId, onAnnotationAdded, onResponseDeleted, onAnnotationDeleted, activeSchema }: ResponseSectionProps) {
  return <ResponseCard
            response={response}
            projectId={projectId}
            onAnnotationAdded={onAnnotationAdded}
            onResponseDeleted={onResponseDeleted}
            onAnnotationDeleted={onAnnotationDeleted}
            activeSchema={activeSchema}
            isAlternative={false}
         />;
}
