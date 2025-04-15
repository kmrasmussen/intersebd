import { ref, computed } from 'vue';
import axios from 'axios';
import { API_BASE_URL } from './config';

interface InterceptKeyDetails {
  intercept_key: string;
  created_at: string;
  is_valid: boolean;
}

const newlyGeneratedKey = ref<string | null>(null);
const isGeneratingKey = ref<boolean>(false);

const userKeys = ref<InterceptKeyDetails[]>([]);
const isLoadingKeys = ref<boolean>(false);



export function useInterceptKeys() {

  const hasValidKey = computed(() => {
    return userKeys.value.some(key => key.is_valid);
  });

  async function generateNewKey() {
    isGeneratingKey.value = true;
    newlyGeneratedKey.value = null;
    try {
      const response = await axios.post<{ intercept_key: string; message: string}>(
        `${API_BASE_URL}/intercept-keys`,
        {},
        { withCredentials: true }
      );
      newlyGeneratedKey.value = response.data.intercept_key;
      await fetchUserKeys();
    }
    catch (error) {
      console.log("error generating new key", error)
      alert("sorry, failed to generate new key")
      newlyGeneratedKey.value = null
    }
    finally {
      isGeneratingKey.value = false;
    }
  }

  async function fetchUserKeys() {
    isLoadingKeys.value = true;
    try {
      const response = await axios.get<{ keys: InterceptKeyDetails[] }>(
        `${API_BASE_URL}/intercept-keys`,
        { withCredentials: true }
      )
      userKeys.value = response.data.keys;
    } catch(error) {
      console.log('Error fetching user intercept keys', error);
      userKeys.value = [];
    } finally {
      isLoadingKeys.value = false;
    }
  }

  return {
    newlyGeneratedKey,
    isGeneratingKey,
    generateNewKey,
    userKeys,
    isLoadingKeys,
    fetchUserKeys,
    hasValidKey
  }
}