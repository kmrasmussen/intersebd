import { reactive, type Ref } from 'vue';
import { API_BASE_URL } from './config';

// Type for the data structure of a single fetched alternative
interface CompletionAlternative {
  id: string;
  alternative_content: string;
  rater_id: string | null;
  created_at: string; // ISO date string
  annotation_target_id: string | null;
}

// Type for the API response when listing alternatives
interface ListAlternativesResponse {
  alternatives: CompletionAlternative[];
}

// State for submission attempts (POST)
interface SubmissionState {
  loading: boolean;
  error: string | null;
  success: boolean;
}

// State for fetching attempts (GET/POST list-by-request)
interface FetchingState {
    loading: boolean;
    error: string | null;
}


export function useCompletionAlternatives(interceptKey: Ref<string | null>) {
  // State for submission attempts, keyed by request ID
  const submissionStates = reactive<Record<string, SubmissionState>>({});
  // State for fetching attempts, keyed by request ID
  const fetchingStates = reactive<Record<string, FetchingState>>({});
  // State to store fetched alternatives, keyed by request ID
  const fetchedAlternatives = reactive<Record<string, CompletionAlternative[]>>({});


  // --- Fetching Alternatives ---
  const fetchAlternatives = async (completionRequestId: string) => {
    if (!interceptKey.value || !completionRequestId) {
      console.error('Missing intercept key or request ID for fetching.');
      // Initialize fetching state with an error if needed, or handle silently
      fetchingStates[completionRequestId] = { loading: false, error: 'Missing key or ID.' };
      return;
    }

    // Initialize or reset fetching state for this request ID
    fetchingStates[completionRequestId] = { loading: true, error: null };
    // Clear previous results for this ID while fetching
    // delete fetchedAlternatives[completionRequestId]; // Or set to []

    try {
      const response = await fetch(`${API_BASE_URL}/completion-alternatives/list-by-request`, {
        method: 'POST', // Using POST as per your endpoint definition
        headers: {
          'Content-Type': 'application/json',
          'accept': 'application/json',
        },
        body: JSON.stringify({
          completion_request_id: completionRequestId,
          intercept_key: interceptKey.value, // Sending intercept_key in body
        }),
      });

      const responseData: ListAlternativesResponse | { detail: string } = await response.json();

      if (!response.ok) {
        const errorMessage = (responseData as { detail: string }).detail || `HTTP error! status: ${response.status}`;
        throw new Error(errorMessage);
      }

      // Store fetched alternatives on success
      fetchedAlternatives[completionRequestId] = (responseData as ListAlternativesResponse).alternatives || [];

    } catch (err: any) {
      console.error('Error fetching alternatives:', err);
      fetchingStates[completionRequestId].error = err.message || 'An unknown error occurred during fetch.';
      // Ensure alternatives list is empty or cleared on error
      fetchedAlternatives[completionRequestId] = [];
    } finally {
      if (fetchingStates[completionRequestId]) {
        fetchingStates[completionRequestId].loading = false;
      }
    }
  };


  // --- Submitting a New Alternative ---
  const submitAlternative = async (completionRequestId: string, alternativeContent: string) => {
    if (!interceptKey.value || !completionRequestId || !alternativeContent.trim()) {
      console.error('Missing intercept key, request ID, or alternative content for submission.');
      submissionStates[completionRequestId] = { loading: false, error: 'Missing key, ID, or content.', success: false };
      return;
    }

    // Initialize or reset submission state
    submissionStates[completionRequestId] = { loading: true, error: null, success: false };

    try {
      const response = await fetch(`${API_BASE_URL}/completion-alternatives/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'accept': 'application/json',
        },
        body: JSON.stringify({
          intercept_key: interceptKey.value,
          completion_request_id: completionRequestId,
          alternative_content: alternativeContent.trim(),
        }),
      });

      const responseData = await response.json();

      if (!response.ok) {
        const errorMessage = responseData.detail || `HTTP error! status: ${response.status}`;
        throw new Error(errorMessage);
      }

      submissionStates[completionRequestId].success = true;
      console.log('Alternative submitted successfully:', responseData);

      // --- Refresh the list after successful submission ---
      await fetchAlternatives(completionRequestId);
      // --- End Refresh ---

    } catch (err: any) {
      console.error('Error submitting alternative:', err);
      submissionStates[completionRequestId].error = err.message || 'An unknown error occurred during submission.';
      submissionStates[completionRequestId].success = false;
    } finally {
      if (submissionStates[completionRequestId]) {
        submissionStates[completionRequestId].loading = false;
      }
    }
  };

  // Function to clear the submission status (e.g., when input changes)
  const clearSubmissionStatus = (completionRequestId: string) => {
    if (submissionStates[completionRequestId]) {
        submissionStates[completionRequestId].success = false;
        submissionStates[completionRequestId].error = null;
    }
  };

  // Helper to get state, providing defaults to prevent template errors
  const getSubmissionState = (requestId: string): SubmissionState => {
    return submissionStates[requestId] || { loading: false, error: null, success: false };
  };

  const getFetchingState = (requestId: string): FetchingState => {
    return fetchingStates[requestId] || { loading: false, error: null };
  };


  return {
    submissionStates, // For POSTing new alternatives
    fetchingStates,   // For fetching list of alternatives
    fetchedAlternatives, // The fetched alternatives data
    submitAlternative,
    fetchAlternatives,
    clearSubmissionStatus,
    // Helpers to safely access state in template
    getSubmissionState,
    getFetchingState,
  };
}