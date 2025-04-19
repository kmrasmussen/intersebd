<!-- filepath: /home/kasper/randomrepos/intersebd/intercebdfrontend/src/components/SftDatasetDownloader.vue -->
<script setup lang="ts">
import { ref, type PropType } from 'vue';
import { API_BASE_URL } from '../config';

const props = defineProps({
  interceptKey: {
    type: String as PropType<string | null>,
    required: true,
  },
});

const isDownloadingJsonl = ref(false);
const downloadJsonlError = ref<string | null>(null);

const downloadSftJsonl = async () => {
  if (!props.interceptKey) {
    downloadJsonlError.value = "Intercept key not available.";
    return;
  }

  isDownloadingJsonl.value = true;
  downloadJsonlError.value = null;

  try {
    const response = await fetch(`${API_BASE_URL}/finetuning/sftdataset.jsonl`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${props.interceptKey}`,
        'Accept': 'application/jsonl',
      },
    });

    if (!response.ok) {
      let errorMsg = `HTTP error ${response.status}`;
      try {
        const errorData = await response.json(); // Or .text()
        errorMsg += `: ${errorData.detail || JSON.stringify(errorData)}`;
      } catch (e) { /* Ignore */ }
      throw new Error(errorMsg);
    }

    const jsonlText = await response.text();
    const blob = new Blob([jsonlText], { type: 'application/jsonl' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.href = url;
    link.download = 'sft_dataset.jsonl';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);

  } catch (error: any) {
    console.error("Error downloading JSONL:", error);
    downloadJsonlError.value = error.message || "An unknown error occurred during download.";
  } finally {
    isDownloadingJsonl.value = false;
  }
};
</script>

<template>
  <div class="download-section">
    <h4>Download SFT Dataset</h4>
    <p>Once you have been down below and annotated responses and alternatives with reward 1, you can download a jsonl files with the conversations to use for fine-tuning.</p>
    <button @click="downloadSftJsonl" :disabled="isDownloadingJsonl || !interceptKey">
      {{ isDownloadingJsonl ? 'Downloading...' : 'Download JSONL Dataset' }}
    </button>
    <span v-if="downloadJsonlError" style="color: red; margin-left: 10px;">
      Error: {{ downloadJsonlError }}
    </span>
    <p v-if="!interceptKey" style="font-style: italic; color: #888;">
      (Button will be enabled once the intercept key is loaded)
    </p>
  </div>
</template>

<style scoped>
.download-section {
  margin-top: 20px;
  margin-bottom: 20px;
  padding: 10px;
  border: 1px solid #eee;
}
button:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}
</style>