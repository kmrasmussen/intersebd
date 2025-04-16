<script setup lang="ts">
import { onMounted } from 'vue';
import { useRoute } from 'vue-router';
import { useCompletionPairs } from '../useCompletionPairs';


const route = useRoute();

const viewingId = route.params.viewingId as string;

const { pairs, interceptKey, isLoading, error, startPolling, stopPolling} = useCompletionPairs(viewingId);

onMounted(() => {
  if (viewingId) {
    startPolling(5000);
  } else {
    console.log('viewing id is missing from route parameters. cannot start polling');
  }
})
</script>

<template>
  <div>
    <h1>intercebd guest</h1>
    
    <div v-if="interceptKey">
      just show them this
      <pre>
            <code>
curl -X POST http://localhost:9003/v1/chat/completions \
  -H "Authorization: Bearer {{ interceptKey }}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "openai/gpt-4.1-nano",
    "messages": [
      {
        "role": "user",
        "content": "What is 2+12?"
      }
    ]
  }'
            </code>
          </pre>
    </div>
    
    <hr>

    <pre v-if="!viewingId">
      i cannot see a viewing id in the url
    </pre>



    <div v-else>
      <div v-if="interceptKey">
        <div>
          <p>you have been gifted this intercept api code for making llm calls</p>
          <pre><code>intercept key: {{ interceptKey }}</code></pre>
          this code is like an openai api key, it is meant to be <i>secret</i>,
          connected to it is a viewing id in the URL
          <div v-if="viewingId">
            <pre><code>viewing id: {{  viewingId }}</code></pre>
          </div>
          normally you would have to be logged in to see this intercept key, but you are a guest
        </div>
        <hr>
        <div>
          <p>the openai chat completions api is a json rest endpoint as shown with the curl code below. many providers like openai, anthropic, google, openrouter all offer such endpoints</p>
          <p><a href="">openrouter.ai</a> allows you to use different model providers</p>
          <p>when using intercebd you have to point to the intercebd endpoint for chat completions and use the intercebd key instead of openai key</p>
          <p>
            intercebd uses openrouter, you can see which models are available on their model page
            <a href="https://openrouter.ai/models">
              https://openrouter.ai/models
            </a>
          </p>
        </div>
    </div>

      <p><i>the list is updated every 5 seconds</i></p>

      <p>i have fetched the pairs</p>
      
      <div v-for="(pair, index) in pairs" :key="pair.request.id">
        <p>this is a pair</p>
        <pre><code>{{ JSON.stringify(pair) }}</code></pre>
      </div>
    </div>
  </div>
</template>