<script setup lang="ts">
import { ref, onMounted, computed, reactive } from 'vue';
import { useRoute } from 'vue-router';
import { useCompletionPairs } from '../useCompletionPairs';
import { useExampleLlmCall } from '../useExampleLlmCall';
import { useClipboard } from '../useClipboard';
import { useAnnotation } from '../useAnnotation'; // Import the new composable
import { useCompletionAlternatives } from '../useCompletionAlternatives';
import { API_BASE_URL } from '../config';

const route = useRoute();
const viewingId = route.params.viewingId as string;

// --- State ---
const prompt = ref('What is 2+12?'); // Reactive prompt variable
const selectedExample = ref<'curl' | 'python' | 'javascript'>('python'); // Default to python

const alternativeInputs = reactive<Record<string, string>>({});

// --- Composables ---
const { pairs, interceptKey, isLoading, error: pairsError, startPolling } = useCompletionPairs(viewingId);
// Pass the prompt ref to the composable
const { exampleCallResult, exampleCallError, isCallingExample, makeExampleCall } = useExampleLlmCall(interceptKey, prompt);
const { copiedCurl, copiedPython, copiedJs, handleCopyClick } = useClipboard();
// Use the annotation composable
const { annotationLoading, annotationError, annotationSuccess, annotateRewardOne } = useAnnotation(interceptKey);
const {
  fetchedAlternatives, // New state for fetched data
  submitAlternative,
  fetchAlternatives, // New function
  clearSubmissionStatus,
  getSubmissionState, // Existing helper
  getFetchingState,   // New helper
} = useCompletionAlternatives(interceptKey);

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

const handleAlternativeSubmit = async (requestId: string) => {
  const content = alternativeInputs[requestId];
  if (content?.trim()) { // Check trim here too
    await submitAlternative(requestId, content);
    // Optionally clear input after successful submission, or leave it
    if (getSubmissionState(requestId).success) {
       alternativeInputs[requestId] = ''; // Clear input on success
    }
  }
}

const onAlternativeInputChange = (requestId: string) => {
  clearSubmissionStatus(requestId); // Clear submission status on input change
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

           <!-- *** START: Modified Annotation Controls *** -->
           <div v-if="pair.response" class="annotation-controls">
             <div v-if="pair.response.annotation_target_id">
               <button
                 @click="annotateRewardOne(pair.response.id, pair.response.annotation_target_id)"
                 :disabled="annotationLoading[pair.response.id] || !interceptKey || !pair.response.annotation_target_id"
               >
                 {{ annotationLoading[pair.response.id] ? 'Annotating...' : 'Annotate with reward 1' }}
               </button>
               <span v-if="annotationSuccess[pair.response.id]" style="color: green; margin-left: 10px;">✓ Annotated!</span>
               <span v-if="annotationError[pair.response.id]" style="color: red; margin-left: 10px;">{{ annotationError[pair.response.id] }}</span>
             </div>
             <div v-else> <!-- Handles case where response exists but target_id doesn't -->
               <span style="color: orange; font-style: italic;">Annotation target ID missing. Cannot annotate.</span>
             </div>
           </div>
           <!-- *** END: Modified Annotation Controls *** -->

            <!-- Alternatives Section -->
            <div class="alternatives-section">
             <h5>Alternatives:</h5>
             <!-- Button to trigger fetching -->
             <button
               @click="fetchAlternatives(pair.request.id)"
               :disabled="getFetchingState(pair.request.id).loading || !interceptKey"
               class="fetch-alternatives-btn"
             >
               {{ getFetchingState(pair.request.id).loading ? 'Loading Alternatives...' : 'Show/Refresh Alternatives' }}
             </button>
             <span v-if="getFetchingState(pair.request.id).error" style="color: red; margin-left: 10px;">
               Error loading alternatives: {{ getFetchingState(pair.request.id).error }}
             </span>

             <!-- Display fetched alternatives -->
             <div v-if="fetchedAlternatives[pair.request.id] && fetchedAlternatives[pair.request.id].length > 0" class="alternatives-list">
                <ul>
                  <li v-for="alt in fetchedAlternatives[pair.request.id]" :key="alt.id">
                    <pre><code>{{ alt.alternative_content }}</code></pre>
                    <small>Submitted: {{ new Date(alt.created_at).toLocaleString() }}</small>
                    <!-- Add rater_id display if needed -->
                    <!-- <small v-if="alt.rater_id"> | Rater: {{ alt.rater_id }}</small> -->
                  </li>
                </ul>
             </div>
             <p v-else-if="!getFetchingState(pair.request.id).loading && fetchedAlternatives[pair.request.id]?.length === 0">
               <i>No alternatives submitted yet (or click button above to load).</i>
             </p>

             <!-- Submission Area -->
             <div class="alternative-submission">
               <h6>Submit New Alternative:</h6>
               <textarea
                 v-model="alternativeInputs[pair.request.id]"
                 @input="onAlternativeInputChange(pair.request.id)"
                 placeholder="Enter a better completion here..."
                 rows="3"
                 :disabled="!interceptKey"
               ></textarea>
               <button
                 @click="handleAlternativeSubmit(pair.request.id)"
                 :disabled="getSubmissionState(pair.request.id).loading || !alternativeInputs[pair.request.id]?.trim() || !interceptKey"
               >
                 {{ getSubmissionState(pair.request.id).loading ? 'Submitting...' : 'Submit New Alternative' }}
               </button>
               <!-- Display submission status -->
               <span v-if="getSubmissionState(pair.request.id).success" style="color: green; margin-left: 10px;">✓ Submitted!</span>
               <span v-if="getSubmissionState(pair.request.id).error" style="color: red; margin-left: 10px;">Error: {{ getSubmissionState(pair.request.id).error }}</span>
             </div>
           </div>
           <!-- *** END: Alternatives Section *** -->

          
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