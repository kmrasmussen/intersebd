import { ref, onUnmounted } from 'vue';
import axios from 'axios';
import { API_BASE_URL } from './config';
import type { CompletionPairDto, CompletionPairListResponseDto } from './types';


export function useCompletionPairs(viewingId: string) {
  const pairs = ref<CompletionPairDto[]>([]);
  const interceptKey = ref<string | null>(null);
  const isLoading = ref<boolean>(false);
  const error = ref<string | null>(null);
  let pollInterval: number | undefined;

  async function fetchCompletionPairs() {
    if (!viewingId) {
      pairs.value = [];
      error.value = "Viewing ID is missing";
      isLoading.value = false;
      return;
    }

    if (pairs.value.length == 0) {
      isLoading.value = true;
    }
    error.value = null;

    try {
      console.log(`Fetching completion pairs for viewing id ${viewingId}`);

      const response = await axios.get<CompletionPairListResponseDto>(
        `${API_BASE_URL}/completion-pairs/view/${viewingId}`,
        { withCredentials: true}
      );
      pairs.value = response.data.pairs;
      interceptKey.value = response.data.intercept_key;
      console.log(`Fetched ${pairs.value.length} completion pairs`);
    } catch (err : any) {
      console.log('Error fetching completion pairs:', err);
      if(err.response?.status === 404) {
        error.value = `Viewing ID ${viewingId} not found`;
      } else {
        error.value = err.response?.data?.detail || err.message || 'Failed to fetch completion pairs';
      }
      pairs.value = [];
    } finally {
      isLoading.value = false;
    }
  }

  function startPolling(intervalMs : number) {
    if (!viewingId) {
      console.log('Not going to poll since viewingId is missing');
      return
    }
    stopPolling();
    fetchCompletionPairs();
    pollInterval = window.setInterval(fetchCompletionPairs, intervalMs);
    console.log(`Started polling for completion pairs every ${intervalMs} ms for viewing id ${viewingId}`);
  }

  function stopPolling() {
    if (pollInterval) {
      clearInterval(pollInterval);
      pollInterval = undefined;
      console.log(`Stopped polling for completion pairs for viewing id ${viewingId}`);
    }
  }

  onUnmounted(() => {
    stopPolling();
  });

  return {
    pairs,
    interceptKey,
    isLoading,
    error,
    fetchCompletionPairs,
    startPolling,
    stopPolling
  }
}
