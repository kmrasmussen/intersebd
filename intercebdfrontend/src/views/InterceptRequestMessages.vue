<template>
  <div>
    <h1>API Unique Request Messages</h1>
    <div v-if="loading">Loading...</div>
    <div v-else-if="error">{{ error }}</div>
    <div v-else>
      <div v-if="requestMessages.length === 0">
        No request messages found
      </div>
      <div v-else>
        <div v-for="(item, index) in requestMessages" :key="item.messages_hash">
          <h3>Request #{{ index + 1 }} (Count: {{ item.count }})</h3>
          <div>
            <div v-for="(message, msgIndex) in item.messages" :key="msgIndex">
              <strong>Role:</strong> {{ message.role }}
              <pre>{{ message.content }}</pre>
            </div>
          </div>
          <div>Hash: {{ item.messages_hash }}</div>
          <hr>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import axios from 'axios';
import { useRoute } from 'vue-router';

interface Message {
  role: string;
  content: string;
}

interface RequestMessage {
  messages_hash: string;
  messages: Message[];
  count: number;
}

const route = useRoute();
const requestMessages = ref<RequestMessage[]>([]);
const loading = ref(true);
const error = ref<string | null>(null);

// Get intercept key from route params
const interceptKey = route.params.interceptKey as string;

const fetchData = async () => {
  loading.value = true;
  try {
    const response = await axios.get(`/api/intercept/${interceptKey}/unique_request_messages`);
    requestMessages.value = response.data;
  } catch (err) {
    console.error('Error fetching request messages:', err);
    error.value = 'Failed to load data from API. Please check that your backend is running.';
  } finally {
    loading.value = false;
  }
};

onMounted(() => {
  fetchData();
});
</script>

<style>
/* No styling */
</style>