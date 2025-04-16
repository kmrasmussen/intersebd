import { ref } from 'vue';
import type { Ref } from 'vue';
import axios from 'axios';
import { API_BASE_URL } from './config';

// Define the structure of the response data if known, otherwise use 'any'
interface LlmResponse {
  // Define expected fields, e.g., id, object, created, model, choices, usage
  [key: string]: any;
}

// Accept the prompt ref as the second argument
export function useExampleLlmCall(interceptKey: Ref<string | null>, prompt: Ref<string>) {
  const exampleCallResult = ref<LlmResponse | null>(null);
  const exampleCallError = ref<string | null>(null);
  const isCallingExample = ref(false);

  async function makeExampleCall() {
    if (!interceptKey.value) {
      console.error("Intercept key is not available for example call.");
      exampleCallError.value = "Intercept key is not available yet.";
      return;
    }
    // Check if prompt has a value (optional, but good practice)
    if (!prompt.value) {
        console.warn("Prompt is empty for example call.");
        // Decide if you want to prevent the call or allow empty prompts
        // exampleCallError.value = "Prompt cannot be empty.";
        // return;
    }

    isCallingExample.value = true;
    exampleCallResult.value = null;
    exampleCallError.value = null;

    const url = `${API_BASE_URL}/v1/chat/completions`;
    const headers = {
      'Authorization': `Bearer ${interceptKey.value}`,
      'Content-Type': 'application/json'
    };
    // Use the prompt ref's current value in the data payload
    const data = {
      model: "openai/gpt-4.1-nano",
      messages: [
        {
          "role": "user",
          "content": prompt.value // Use the reactive prompt value here
        }
      ]
    };

    console.log("Making example call via composable with prompt:", prompt.value);

    try {
      const response = await axios.post<LlmResponse>(url, data, { headers });
      console.log("Example call successful (composable):", response.data);
      exampleCallResult.value = response.data;
    } catch (error: any) {
      console.error("Example call failed (composable):", error);
      let errorMessage = "An unknown error occurred.";
      if (axios.isAxiosError(error)) {
        errorMessage = error.response?.data?.error?.message || error.message || JSON.stringify(error.response?.data);
      } else if (error instanceof Error) {
        errorMessage = error.message;
      }
      exampleCallError.value = `Failed to make example call: ${errorMessage}`;
      exampleCallResult.value = null;
    } finally {
      isCallingExample.value = false;
    }
  }

  // Return the state and the function
  return {
    exampleCallResult,
    exampleCallError,
    isCallingExample,
    makeExampleCall
  };
}