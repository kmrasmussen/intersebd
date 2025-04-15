import { ref } from 'vue';
import axios from 'axios';
import { API_BASE_URL } from './config'; // Assuming you have a config file for the base URL

// Interface matching the backend response structure
interface OpenRouterGuestKeyDetails {
  id: string; // UUID as string
  or_key_hash: string;
  or_name: string;
  or_label: string;
  or_disabled: boolean;
  or_limit: number;
  or_created_at: string; // ISO date string
  or_updated_at: string | null; // ISO date string or null
  or_key: string;
  or_usage: number;
  is_active: boolean;
  // Add created_at_db if it's included in your final DTO and needed on the frontend
  // created_at_db: string;
}

const generatedGuestKey = ref<OpenRouterGuestKeyDetails | null>(null);
const isGeneratingGuestKey = ref<boolean>(false);
const generationError = ref<string | null>(null);

export function useProviderKeys() {

  async function generateGuestOpenRouterKey() {
    isGeneratingGuestKey.value = true;
    generatedGuestKey.value = null;
    generationError.value = null;

    try {
      // Make the POST request to the backend endpoint
      const response = await axios.post<OpenRouterGuestKeyDetails>(
        `${API_BASE_URL}/provider_keys/openrouter/generate_guest`, // Corrected endpoint path
        {}, // No request body needed for this endpoint
        { withCredentials: true } // Include if authentication/session is required
      );
      generatedGuestKey.value = response.data;
      console.log("Successfully generated OpenRouter guest key:", response.data);
    } catch (error: any) {
      console.error("Error generating OpenRouter guest key:", error);
      generationError.value = error.response?.data?.detail || error.message || "Failed to generate guest key.";
      // Optionally display an alert or use a more sophisticated error handling mechanism
      // alert(`Error: ${generationError.value}`);
    } finally {
      isGeneratingGuestKey.value = false;
    }
  }

  // You could add functions here later to fetch existing keys, revoke keys, etc.

  return {
    generatedGuestKey,
    isGeneratingGuestKey,
    generationError,
    generateGuestOpenRouterKey,
  };
}