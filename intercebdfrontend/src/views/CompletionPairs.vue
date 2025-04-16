<script setup lang="ts">
import { ref, onMounted, Ref, computed, isRef } from 'vue'; // Import computed
import { useRoute } from 'vue-router';
import { useCompletionPairs } from '../useCompletionPairs';
import { API_BASE_URL } from '../config';
const route = useRoute();
const viewingId = route.params.viewingId as string;
const { pairs, interceptKey, isLoading, error, startPolling, stopPolling} = useCompletionPairs(viewingId);

// State to control which code example is shown
const selectedExample = ref<'curl' | 'python' | 'javascript'>('python'); // Default to curl

// --- Computed properties for code strings (Single Source of Truth) ---
const curlCodeString = computed(() => {
  if (!interceptKey.value) return '';
  return `curl \\
-X POST ${API_BASE_URL}/v1/chat/completions \\
-H "Authorization: Bearer ${interceptKey.value}" \\
-H "Content-Type: application/json" \\
-d '{
    "model": "openai/gpt-4.1-nano",
    "messages": [
      {
        "role": "user",
        "content": "What is 2+12?"
      }
    ]
  }'`;
});

const pythonCodeString = computed(() => {
  if (!interceptKey.value) return '';
  return `from openai import OpenAI

client = OpenAI(
  base_url="${API_BASE_URL}/v1",
  api_key="${interceptKey.value}"
)

completion = client.chat.completions.create(
  model="openai/gpt-4.1-nano",
  messages=[
    {
      "role": "user",
      "content": "What is 2+12?"
    }
  ]
)
print(completion)`;
});

const jsCodeString = computed(() => {
  return `const url = '${API_BASE_URL}/v1/chat/completions';
const options = {
  method: 'POST',
  headers: {Authorization: 'Bearer ${interceptKey.value}', 'Content-Type': 'application/json'},
  body: '{"model":"openai/gpt-4.1-nano"}'
};
try {
  const response = await fetch(url, options);
  const data = await response.json();
  console.log(data);
} catch (error) {
  console.error(error);
}`;
});
// --- End Computed properties ---

// --- Clipboard Logic ---
// Refs to track copied status for each button
const copiedCurl = ref(false);
const copiedPython = ref(false);
const copiedJs = ref(false);
// Simplified copyCode - only handles writing to clipboard
async function copyCode(textToCopy: string): Promise<boolean> { // Returns true on success, false on failure
  if (!textToCopy) {
    console.error('Cannot copy empty string.');
    return false;
  }
  try {
    await navigator.clipboard.writeText(textToCopy);
    console.log('Code copied successfully.');
    return true;
  } catch (err) {
    console.error('Failed to copy: ', err);
    return false;
  }
}

onMounted(() => {
  if (viewingId) {
    startPolling(5000);
  } else {
    console.log('viewing id is missing from route parameters. cannot start polling');
  }
});
</script>

<template>
  <div>
    point your llm api calls to <b>intercebd</b> to start logging, annotating and fine-tuning your llm usage.
    <div>
      <button @click="selectedExample = 'curl'" :disabled="selectedExample === 'curl'">curl</button>
      <button @click="selectedExample = 'python'" :disabled="selectedExample === 'python'">python</button>
      <button @click="selectedExample = 'javascript'" :disabled="selectedExample === 'javascript'">javascript</button>

      <div v-if="selectedExample === 'curl' && interceptKey" class="code-example">
        <pre><code>{{ curlCodeString }}</code></pre>
        <button @click="copyCode(curlCodeString, copiedCurl)" class="copy-btn">
          {{ copiedCurl ? 'copied' : 'copy' }}
        </button>
      </div>
      <div v-if="selectedExample === 'python' && interceptKey" class="code-example">
        <pre><code>{{ pythonCodeString }}</code></pre>
  <button @click="copyCode(pythonCodeString, copiedPython)" class="copy-btn">
           {{ copiedPython ? 'copied' : 'copy' }}
        </button>
      </div>
      <div v-if="selectedExample === 'javascript' && interceptKey" class="code-example">
        <pre><code>{{ jsCodeString }}</code></pre><button @click="copyCode(jsCodeString, copiedJs)" class="copy-btn">
           {{ copiedJs ? 'copied' : 'copy' }}
        </button>
      </div>

       <div v-if="!interceptKey && (isLoading || error)">
         <p><i>(Code examples will appear here once the intercept key is loaded)</i></p>
       </div>
    </div>
    

<!-- Collapsible Explanation Section -->
<details>
      <summary>What is this?</summary>
      <div>
        <p>You have been gifted this intercept API key for making LLM calls. This key is like an OpenAI API key; it is meant to be <strong>secret</strong>.</p>
        <p>Connected to it is the public viewing ID shown in the URL and above, which allows viewing the request/response pairs associated with this key.</p>
        <p>Normally, you would have to be logged in to see the intercept key, but you are viewing as a guest.</p>
        <hr>
        <p>The OpenAI Chat Completions API is a JSON REST endpoint. Many providers like OpenAI, Anthropic, Google, and OpenRouter offer similar endpoints.</p>
        <p><a href="https://openrouter.ai/" target="_blank" rel="noopener noreferrer">OpenRouter.ai</a> allows you to use models from different providers through a unified API.</p>
        <p>When using Intercebd, you point your application to the Intercebd endpoint (like `http://localhost:9003/v1/chat/completions`) and use your Intercebd key (shown above) instead of your usual provider key.</p>
        <p>Intercebd uses OpenRouter internally. You can see available models on their model page: <a href="https://openrouter.ai/models" target="_blank" rel="noopener noreferrer">https://openrouter.ai/models</a>.</p>
      </div>
      <div v-if="interceptKey">
      <p><strong>Chat Completions Endpoint</strong></p>
      <pre><code>{{ API_BASE_URL }}/v1/chat/completions</code></pre>
      <p><strong>Guest API Key (Secret for non-guests):</strong></p>
      <pre><code>{{ interceptKey }}</code></pre>
    </div>
    </details>

    <!-- Pairs Display Section -->
    <div>
      <h4>Request/Response Pairs</h4>
      <p><i>(List updates automatically every 5 seconds)</i></p>

      <div v-if="isLoading && pairs.length === 0">
        <p>Fetching pairs...</p>
      </div>
      <div v-else-if="error">
        <p style="color: red;">Error fetching data: {{ error }}</p>
      </div>
      <div v-else-if="pairs.length === 0">
        <p>No completion pairs found yet.</p>
      </div>
      <div v-else>
        <div v-for="(pair, index) in pairs" :key="pair.request.id" class="pair-container">
           <!-- Display request/response details -->
           <p><strong>Pair {{ pairs.length - index }}</strong></p>
           <h5>Request:</h5>
           <pre><code>{{ JSON.stringify(pair.request, null, 2) }}</code></pre>
           <h5>Response:</h5>
           <pre v-if="pair.response"><code>{{ JSON.stringify(pair.response, null, 2) }}</code></pre>
           <p v-else><i>(No response yet)</i></p>
           <hr v-if="index < pairs.length - 1">
        </div>
      </div>
    </div>

     <!-- Link back to Home -->
    <router-link :to="{ name: 'home' }">Back to Home</router-link>

  </div>
</template>

<style scoped>
/* Add some basic styling */
details {
  border: 1px solid #ccc;
  border-radius: 4px;
  margin-bottom: 1em;
}
summary {
  font-weight: bold;
  padding: 0.5em;
  cursor: pointer;
  background-color: #f9f9f9;
}
details > div { /* Style the content inside details */
  padding: 1em;
  border-top: 1px solid #ccc;
}
button {
  margin-right: 5px;
  padding: 5px 10px;
  cursor: pointer;
}
button:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}
pre {
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-all;
  background-color: #f4f4f4;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 0.9em;
  margin-top: 5px;
}
.code-example { position: relative; margin-bottom: 1em; }
.copy-btn { position: absolute; bottom: 8px; right: 8px; padding: 3px 6px; font-size: 0.8em; background-color: #eee; border: 1px solid #ccc; border-radius: 4px; cursor: pointer; }
.code-example:hover .copy-btn { opacity: 1; }
.copy-btn:active { background-color: #ddd; }
pre { overflow-x: auto; white-space: pre-wrap; word-break: break-all; background-color: #f4f4f4; padding: 10px; border: 1px solid #ddd; border-radius: 4px; font-size: 0.9em; margin-top: 5px; }
</style>