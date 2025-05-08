"use client"

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea"; // Assuming you have this component
import { RefreshCw } from "lucide-react";

// Import the ResponseDetail type (or define it if not imported)
// Assuming ResponseDetail is similar to the Response type used elsewhere
type Annotation = { id: string; reward: number; by: string; at: string; };
type ResponseDetail = {
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

type NewAlternativeFormProps = {
  projectId: string;
  requestId: string;
  onAlternativeAdded: (newAlternative: ResponseDetail) => void; // Callback with new data
}

export function NewAlternativeForm({ projectId, requestId, onAlternativeAdded }: NewAlternativeFormProps) {
  const [newAlternativeContent, setNewAlternativeContent] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const handleSubmit = async () => {
    if (!newAlternativeContent.trim()) {
      setSubmitError("Alternative content cannot be empty.");
      return;
    }

    setIsSubmitting(true);
    setSubmitError(null);

    const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";
    const GUEST_USER_ID_HEADER = "X-Guest-User-Id";
    const apiUrl = `${API_BASE_URL}/mock-next/${projectId}/requests/${requestId}/alternatives`;
    const guestUserId = localStorage.getItem('guestUserId');
    const headers: HeadersInit = {
        'Content-Type': 'application/json',
    };
    if (guestUserId) {
      headers[GUEST_USER_ID_HEADER] = guestUserId;
    }

    console.log(`Submitting new alternative for request ${requestId} at ${apiUrl}`);

    try {
      const response = await fetch(apiUrl, {
        method: 'POST',
        headers: headers,
        body: JSON.stringify({ alternative_content: newAlternativeContent }),
        credentials: 'include',
      });

      if (!response.ok) {
         let errorDetail = `HTTP error! status: ${response.status}`;
         try {
           const errorData = await response.json();
           errorDetail += ` - ${errorData.detail || 'Unknown error'}`;
         } catch (jsonError) { /* Ignore */ }
         throw new Error(errorDetail);
      }

      const createdAlternative: ResponseDetail = await response.json();
      console.log("Alternative created successfully:", createdAlternative);

      // Call the callback to update parent state
      onAlternativeAdded(createdAlternative);

      // Clear the form
      setNewAlternativeContent("");

    } catch (error: any) {
      console.error("Failed to submit alternative:", error);
      setSubmitError(error.message || "Failed to submit alternative");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div>
      <h3 className="font-medium mb-2">Submit New Alternative:</h3>
      <div className="flex flex-col sm:flex-row gap-2">
        <Textarea // Use Textarea component
          className="flex-1 p-2 border rounded-md min-h-[80px] sm:min-h-[40px]" // Adjusted height
          placeholder="Enter a better completion here..."
          value={newAlternativeContent}
          onChange={(e) => setNewAlternativeContent(e.target.value)}
          disabled={isSubmitting}
        />
        <div className="flex flex-col justify-end mt-2 sm:mt-0">
          <Button
            variant="outline"
            className="whitespace-nowrap"
            onClick={handleSubmit}
            disabled={isSubmitting || !newAlternativeContent.trim()}
          >
            {isSubmitting ? <RefreshCw className="h-4 w-4 animate-spin mr-2" /> : null}
            Submit Alternative
          </Button>
        </div>
      </div>
      {submitError && <p className="text-red-500 text-sm mt-2">{submitError}</p>}
    </div>
  )
}
