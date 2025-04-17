<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import axios from 'axios';
import { API_BASE_URL } from '../config';


const router = useRouter();
const isLoading = ref(true);
const error = ref<string | null>(null);

interface GuestKeyResponse {
  intercept_key: string;
  viewing_id: string;
  matching_openrouter_key: string;
  message : string;
}

onMounted(async () => {
  isLoading.value = true;
  error.value = null;
  console.log('GuestRedirect mounted, fetching guest key...');
  try {
    const response = await axios.post<GuestKeyResponse>(
      `${API_BASE_URL}/intercept-keys/guest`,
      {},
      { withCredentials: true }
    );

    const viewingId = response.data.viewing_id;
    console.log(`Guest key created, received viewing id: ${viewingId}. Redirecting`);

    if (viewingId) {
      router.replace({
        name: 'completion-pairs-view',
        params: { viewingId: viewingId },
      })
      // Note: isLoading will remain true as the component unmounts upon redirect
    } else {
      console.error('Failed to get viewing id');
      error.value = 'Failed to retrieve guest api key';
      isLoading.value = false; 
    }
  } catch (err : any) {
    console.log('error creating guest key:', err);
    error.value = err.response?.data?.detail || err.message || 'An error occurred';
    isLoading.value = false;
  }
});

</script>

<template>
  <div>
    <div v-if="isLoading">
      <p>i am trying to fetch a guest api key so you can try intercebd, please wait...</p>
    </div>
    <div v-else-if="error">
      <p>i'm sorry, there was an error when trying to get the guest api key, for you to try intercebd. the error message is {{ error }}</p>
    </div>
  </div>
</template>