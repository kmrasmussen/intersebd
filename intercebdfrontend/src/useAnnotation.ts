import { ref } from 'vue';
import type { Ref } from 'vue';
import axios from 'axios';
import { API_BASE_URL } from './config';

// Existing AnnotationResponse interface
export interface AnnotationResponse {
  id: string;
  timestamp: string;
  rater_id?: string | null;
  reward?: number | null;
  annotation_metadata?: Record<string, any> | null;
}

// --- NEW: Type for the fetch request body ---
interface GetAnnotationsByTargetRequest {
  annotation_target_id: string;
  intercept_key: string;
}

export function useAnnotation(interceptKey: Ref<string | null>) {
  // --- State for CREATING annotations ---
  // Keyed by the item's own ID (response ID or alternative ID) for UI feedback
  const createAnnotationLoading = ref<Record<string, boolean>>({});
  const createAnnotationError = ref<Record<string, string | null>>({});
  const createAnnotationSuccess = ref<Record<string, boolean>>({});

  // --- NEW: State for FETCHING annotations ---
  // Keyed by annotationTargetId
  const fetchedAnnotations = ref<Record<string, AnnotationResponse[]>>({});
  const fetchAnnotationsLoading = ref<Record<string, boolean>>({});
  const fetchAnnotationsError = ref<Record<string, string | null>>({});

  // --- Function for CREATING annotations ---
  async function annotateRewardOne(
    uiStateKey: string, // ID of the specific item (response/alternative) for UI state
    annotationTargetId: string,
    raterId: string = 'guest-rater'
  ) {
    if (!interceptKey.value) {
      console.error("Intercept key is missing, cannot annotate.");
      createAnnotationError.value = { ...createAnnotationError.value, [uiStateKey]: "Intercept key is missing." };
      return;
    }
    if (!annotationTargetId) {
      console.error("Annotation Target ID is missing, cannot annotate.");
      createAnnotationError.value = { ...createAnnotationError.value, [uiStateKey]: "Annotation Target ID is missing." };
      return;
    }

    console.log(`Annotating target ${annotationTargetId} with reward 1 for key ${interceptKey.value}`);

    createAnnotationLoading.value = { ...createAnnotationLoading.value, [uiStateKey]: true };
    createAnnotationError.value = { ...createAnnotationError.value, [uiStateKey]: null };
    createAnnotationSuccess.value = { ...createAnnotationSuccess.value, [uiStateKey]: false };

    const url = `${API_BASE_URL}/annotations/`;
    const data = {
      annotation_target_id: annotationTargetId,
      rater_id: raterId,
      reward: 1,
      annotation_metadata: {},
      intercept_key: interceptKey.value
    };

    try {
      const response = await axios.post<AnnotationResponse>(url, data);
      console.log(`Annotation successful for target ${annotationTargetId}:`, response.data);
      createAnnotationSuccess.value = { ...createAnnotationSuccess.value, [uiStateKey]: true };

      // --- NEW: Optionally refresh annotations after successful creation ---
      // You might want to automatically call fetchAnnotationsForTarget here
      // await fetchAnnotationsForTarget(annotationTargetId);
      // Or let the user click refresh manually

    } catch (error: any) {
      console.error(`Annotation failed for target ${annotationTargetId}:`, error);
      let errorMessage = "An unknown error occurred during annotation.";
      if (axios.isAxiosError(error)) {
        errorMessage = error.response?.data?.detail || error.message || JSON.stringify(error.response?.data);
      } else if (error instanceof Error) {
        errorMessage = error.message;
      }
      createAnnotationError.value = { ...createAnnotationError.value, [uiStateKey]: `Annotation failed: ${errorMessage}` };
    } finally {
      createAnnotationLoading.value = { ...createAnnotationLoading.value, [uiStateKey]: false };
    }
  }

  // --- NEW: Function for FETCHING annotations ---
  async function fetchAnnotationsForTarget(annotationTargetId: string) {
     if (!interceptKey.value) {
      console.error("Intercept key is missing, cannot fetch annotations.");
      fetchAnnotationsError.value = { ...fetchAnnotationsError.value, [annotationTargetId]: "Intercept key is missing." };
      return;
    }
     if (!annotationTargetId) {
      console.error("Annotation Target ID is missing, cannot fetch annotations.");
       fetchAnnotationsError.value = { ...fetchAnnotationsError.value, [annotationTargetId]: "Annotation Target ID is missing." };
      return;
    }

    console.log(`Fetching annotations for target ${annotationTargetId}`);
    fetchAnnotationsLoading.value = { ...fetchAnnotationsLoading.value, [annotationTargetId]: true };
    fetchAnnotationsError.value = { ...fetchAnnotationsError.value, [annotationTargetId]: null };

    const url = `${API_BASE_URL}/annotations/target/list`;
    const data: GetAnnotationsByTargetRequest = {
      annotation_target_id: annotationTargetId,
      intercept_key: interceptKey.value
    };

    try {
      const response = await axios.post<AnnotationResponse[]>(url, data);
      fetchedAnnotations.value = { ...fetchedAnnotations.value, [annotationTargetId]: response.data };
      console.log(`Successfully fetched ${response.data.length} annotations for target ${annotationTargetId}`);
    } catch (error: any) {
      console.error(`Failed to fetch annotations for target ${annotationTargetId}:`, error);
      let errorMessage = "An unknown error occurred fetching annotations.";
       if (axios.isAxiosError(error)) {
        errorMessage = error.response?.data?.detail || error.message || JSON.stringify(error.response?.data);
      } else if (error instanceof Error) {
        errorMessage = error.message;
      }
      fetchAnnotationsError.value = { ...fetchAnnotationsError.value, [annotationTargetId]: `Fetch failed: ${errorMessage}` };
      // Clear potentially stale data on error
      fetchedAnnotations.value = { ...fetchedAnnotations.value, [annotationTargetId]: [] };

    } finally {
      fetchAnnotationsLoading.value = { ...fetchAnnotationsLoading.value, [annotationTargetId]: false };
    }
  }


  return {
    // Create state/methods (renamed for clarity)
    createAnnotationLoading,
    createAnnotationError,
    createAnnotationSuccess,
    annotateRewardOne,
    // Fetch state/methods
    fetchedAnnotations,
    fetchAnnotationsLoading,
    fetchAnnotationsError,
    fetchAnnotationsForTarget
  };
}