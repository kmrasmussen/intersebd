import { ref } from 'vue';
import type { Ref } from 'vue';
import axios from 'axios';
import { API_BASE_URL } from './config';

// Update response type based on the actual backend response schema (AnnotationResponseSchema)
interface AnnotationResponse {
  id: string; // UUID string
  timestamp: string; // ISO datetime string
  rater_id?: string | null;
  reward?: number | null;
  annotation_metadata?: Record<string, any> | null;
}

export function useAnnotation(interceptKey: Ref<string | null>) {
  const annotationLoading = ref<Record<string, boolean>>({}); // Keyed by completionResponseId for UI state
  const annotationError = ref<Record<string, string | null>>({}); // Keyed by completionResponseId for UI state
  const annotationSuccess = ref<Record<string, boolean>>({}); // Keyed by completionResponseId for UI state

  async function annotateRewardOne(
    completionResponseId: string, // Keep for UI state keying
    annotationTargetId: string,   // NEW: The actual ID needed for the API call
    raterId: string = 'guest-rater'
  ) {
    if (!interceptKey.value) {
      console.error("Intercept key is missing, cannot annotate.");
      annotationError.value[completionResponseId] = "Intercept key is missing.";
      return;
    }
    // Check annotationTargetId instead of completionResponseId for the API call requirement
    if (!annotationTargetId) {
      console.error("Annotation Target ID is missing, cannot annotate.");
      annotationError.value[completionResponseId] = "Annotation Target ID is missing.";
      return;
    }

    console.log(`Annotating target ${annotationTargetId} with reward 1 for key ${interceptKey.value}`);

    // Set loading/error/success state using completionResponseId as the key
    annotationLoading.value = { ...annotationLoading.value, [completionResponseId]: true };
    annotationError.value = { ...annotationError.value, [completionResponseId]: null };
    annotationSuccess.value = { ...annotationSuccess.value, [completionResponseId]: false };

    const url = `${API_BASE_URL}/annotations/`; // Use the new base annotation endpoint
    const data = {
      annotation_target_id: annotationTargetId, // Use the target ID
      rater_id: raterId,
      reward: 1,
      annotation_metadata: {}, // Add metadata if needed
      intercept_key: interceptKey.value
    };

    try {
      const response = await axios.post<AnnotationResponse>(url, data);
      console.log(`Annotation successful for target ${annotationTargetId}:`, response.data);
      annotationSuccess.value = { ...annotationSuccess.value, [completionResponseId]: true };
    } catch (error: any) {
      console.error(`Annotation failed for target ${annotationTargetId}:`, error);
      let errorMessage = "An unknown error occurred during annotation.";
      if (axios.isAxiosError(error)) {
        errorMessage = error.response?.data?.detail || error.message || JSON.stringify(error.response?.data);
      } else if (error instanceof Error) {
        errorMessage = error.message;
      }
      // Use completionResponseId for UI error state
      annotationError.value = { ...annotationError.value, [completionResponseId]: `Annotation failed: ${errorMessage}` };
    } finally {
      // Use completionResponseId for UI loading state
      annotationLoading.value = { ...annotationLoading.value, [completionResponseId]: false };
    }
  }

  return {
    annotationLoading,
    annotationError,
    annotationSuccess,
    annotateRewardOne
  };
}