import { ref } from 'vue';
import type { Ref } from 'vue';
import axios from 'axios';
import { API_BASE_URL } from './config';

interface AnnotationResponse {
  annotation_id: string;
  status: string;
  message: string;
}

export function useAnnotation(interceptKey: Ref<string | null>) {
  const annotationLoading = ref<Record<string, boolean>>({}); // Track loading per response ID
  const annotationError = ref<Record<string, string | null>>({}); // Track errors per response ID
  const annotationSuccess = ref<Record<string, boolean>>({}); // Track success per response ID

  async function annotateRewardOne(completionResponseId: string, raterId: string = 'guest-rater') {
    if (!interceptKey.value) {
      console.error("Intercept key is missing, cannot annotate.");
      annotationError.value[completionResponseId] = "Intercept key is missing.";
      return;
    }
    if (!completionResponseId) {
      console.error("Completion Response ID is missing, cannot annotate.");
      annotationError.value[completionResponseId] = "Completion Response ID is missing.";
      return;
    }

    console.log(`Annotating ${completionResponseId} with reward 1 for key ${interceptKey.value}`);

    // Set loading state for this specific ID
    annotationLoading.value = { ...annotationLoading.value, [completionResponseId]: true };
    annotationError.value = { ...annotationError.value, [completionResponseId]: null };
    annotationSuccess.value = { ...annotationSuccess.value, [completionResponseId]: false };


    const url = `${API_BASE_URL}/v1/chat/completions/annotation`;
    const data = {
      completion_response_id: completionResponseId,
      rater_id: raterId, // Using a default or pass one in
      reward: 1,
      annotation_metadata: {}, // Add metadata if needed
      intercept_key: interceptKey.value
    };

    try {
      const response = await axios.post<AnnotationResponse>(url, data);
      console.log(`Annotation successful for ${completionResponseId}:`, response.data);
      annotationSuccess.value = { ...annotationSuccess.value, [completionResponseId]: true };
    } catch (error: any) {
      console.error(`Annotation failed for ${completionResponseId}:`, error);
      let errorMessage = "An unknown error occurred during annotation.";
      if (axios.isAxiosError(error)) {
        errorMessage = error.response?.data?.detail || error.message || JSON.stringify(error.response?.data);
      } else if (error instanceof Error) {
        errorMessage = error.message;
      }
      annotationError.value = { ...annotationError.value, [completionResponseId]: `Annotation failed: ${errorMessage}` };
    } finally {
      // Reset loading state for this specific ID
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