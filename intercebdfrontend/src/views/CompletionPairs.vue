<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import { useRoute } from 'vue-router';
import { useCompletionPairs } from '../useCompletionPairs';
import { useExampleLlmCall } from '../useExampleLlmCall';
import { useClipboard } from '../useClipboard';
import { useAnnotation } from '../useAnnotation'; // Import the new composable
import { API_BASE_URL } from '../config';

const route = useRoute();
const viewingId = route.params.viewingId as string;

// --- State ---
const prompt = ref('What is 2+12?'); // Reactive prompt variable
const selectedExample = ref<'curl' | 'python' | 'javascript'>('python'); // Default to python

// --- Composables ---
const { pairs, interceptKey, isLoading, error: pairsError, startPolling } = useCompletionPairs(viewingId);
// Pass the prompt ref to the composable
const { exampleCallResult, exampleCallError, isCallingExample, makeExampleCall } = useExampleLlmCall(interceptKey, prompt);
const { copiedCurl, copiedPython, copiedJs, handleCopyClick } = useClipboard();
// Use the annotation composable
const { annotationLoading, annotationError, annotationSuccess, annotateRewardOne } = useAnnotation(interceptKey);

// --- Computed properties for code strings (updated to use prompt.value) ---
const curlCodeString = computed(() => {
  if (!interceptKey.value) return '';
  // Escape the prompt for JSON string literal
  const escapedPrompt = JSON.stringify(prompt.value);
  return `curl \\
-X POST ${API_BASE_URL}/v1/chat/completions \\
-H "Authorization: Bearer ${interceptKey.value}" \\
-H "Content-Type: application/json" \\
-d '{
    "model": "openai/gpt-4.1-nano",
    "messages": [
      {
        "role": "user",
        "content": ${escapedPrompt}
      }
    ]
  }'`;
});

const pythonCodeString = computed(() => {
  if (!interceptKey.value) return '';
  // Escape backticks and ${} if the prompt might contain them for f-string safety
  const escapedPrompt = prompt.value.replace(/`/g, '\\`').replace(/\$\{/g, '\\${');
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
      "content": f"""${escapedPrompt}"""
    }
  ]
)
print(completion)`;
});

const jsCodeString = computed(() => {
  if (!interceptKey.value) return '';
  // Escape backticks, ${}, and single quotes for JS template literal/string safety
  const escapedPrompt = prompt.value.replace(/`/g, '\\`').replace(/\$\{/g, '\\${').replace(/'/g, "\\'");
  return `const url = '${API_BASE_URL}/v1/chat/completions';
const options = {
  method: 'POST',
  headers: {
    Authorization: 'Bearer ${interceptKey.value}',
    'Content-Type': 'application/json'
  },
  // Use JSON.stringify for the body to handle prompt quoting correctly
  body: JSON.stringify({
    model: "openai/gpt-4.1-nano",
    messages: [
      {
        role: "user",
        content: '${escapedPrompt}'
      }
    ]
  })
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
    <div id="intro">
      point your llm api calls to <b>intercebd</b> to start logging, annotating and fine-tuning your llm usage.
    </div>
    
    <!-- Start code examples -->
    <div id="code-examples">
      <button @click="selectedExample = 'curl'" :disabled="selectedExample === 'curl'">curl</button>
      <button @click="selectedExample = 'python'" :disabled="selectedExample === 'python'">python</button>
      <button @click="selectedExample = 'javascript'" :disabled="selectedExample === 'javascript'">javascript</button>

      <div v-if="selectedExample === 'curl' && interceptKey" class="code-example">
        <pre><code>{{ curlCodeString }}</code></pre>
        <!-- Pass 'curl' identifier -->
        <button @click="handleCopyClick(curlCodeString, 'curl')" class="copy-btn">
          {{ copiedCurl ? 'copied' : 'copy' }}
        </button>
      </div>
      <div v-if="selectedExample === 'python' && interceptKey" class="code-example">
        <pre><code>{{ pythonCodeString }}</code></pre>
        <!-- Pass 'python' identifier -->
        <button @click="handleCopyClick(pythonCodeString, 'python')" class="copy-btn">
           {{ copiedPython ? 'copied' : 'copy' }}
        </button>
      </div>
      <div v-if="selectedExample === 'javascript' && interceptKey" class="code-example">
        <pre><code>{{ jsCodeString }}</code></pre>
        <!-- Pass 'js' identifier -->
        <button @click="handleCopyClick(jsCodeString, 'js')" class="copy-btn">
           {{ copiedJs ? 'copied' : 'copy' }}
        </button>
      </div>

       <!-- Use pairsError here -->
       <div v-if="!interceptKey && (isLoading || pairsError)">
         <p><i>(Code examples will appear here once the intercept key is loaded or if there was an error loading it)</i></p>
       </div>
    </div>
    <!-- End code examples -->

    <div id="run-example">
      <div class="run-controls">
        <button @click="makeExampleCall" :disabled="isCallingExample || !interceptKey">
          {{ isCallingExample ? 'making call now from browser, please wait...' : 'run call shown above' }}
        </button>
        <!-- Bind input to the prompt ref -->
        <input type="text" v-model="prompt" placeholder="Enter prompt here..." class="prompt-input">
      </div>
      <div v-if="exampleCallResult" style="margin-top: 10px;">
        <p><strong>ok, call worked. you can see the response below, but the point is rather that the full list of all calls is below and you can now vote on the good ones</strong></p>
        <details>
          <summary>response from example call</summary>
          <div> <pre><code>{{ JSON.stringify(exampleCallResult, null, 2) }}</code></pre></div>
        </details>
       
      </div>
      <div v-if="exampleCallError" style="margin-top: 10px; color: red;">
        <p><strong>Example Call Error:</strong></p>
        <pre><code>{{ exampleCallError }}</code></pre>
      </div>
    </div>

    <br >
     <!-- Collapsible Explanation Section -->
  

    <!-- Pairs Display Section -->
    <div>
      <h4>Request/Response Pairs</h4>
      <p><i>(List updates automatically every 5 seconds)</i></p>

      <div v-if="isLoading && pairs.length === 0">
        <p>Fetching pairs...</p>
      </div>
      <div v-else-if="pairsError">
        <p style="color: red;">Error fetching data: {{ pairsError }}</p>
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
           <div v-if="pair.response" class="annotation-controls">
             <button
               @click="annotateRewardOne(pair.response.id)"
               :disabled="annotationLoading[pair.response.id] || !interceptKey"
             >
               {{ annotationLoading[pair.response.id] ? 'Annotating...' : 'Annotate with reward 1' }}
             </button>
             <span v-if="annotationSuccess[pair.response.id]" style="color: green; margin-left: 10px;">✓ Annotated!</span>
             <span v-if="annotationError[pair.response.id]" style="color: red; margin-left: 10px;">{{ annotationError[pair.response.id] }}</span>
           </div>
           <hr v-if="index < pairs.length - 1">
        </div>
      </div>
    </div>
  </div>

  <hr>
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