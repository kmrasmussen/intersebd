<script setup lang="ts">
import { onMounted, watch, ref, computed, onUpdated } from 'vue';
import  { useAuth } from '../auth';
import { useInterceptKeys } from '../interceptKeys';
import { API_BASE_URL } from '../config';

// syntax highlighting start
import hljs from 'highlight.js/lib/core';
import python from 'highlight.js/lib/languages/python';
import 'highlight.js/styles/github.css';
hljs.registerLanguage('python', python);
// syntax highlighting end

const { user, isAuthenticated, isLoading, checkLoginStatus, login, logout } = useAuth();

const { 
  newlyGeneratedKey, 
  isGeneratingKey, 
  generateNewKey, 
  userKeys,
  isLoadingKeys, 
  fetchUserKeys, 
  hasValidKey 
} = useInterceptKeys();


const firstValidKey = computed(() => {
  return userKeys.value.find(key => key.is_valid);
})

const promptContent = ref("What is 2+2?");

const codeBlockRef = ref<HTMLElement | null>(null);
  const highlightCode = () => {
  if (codeBlockRef.value) {
    const codeElement = codeBlockRef.value.querySelector('code.language-python'); // Be more specific
    if (codeElement) {
        // --- Add this check and removal ---
        if (codeElement.hasAttribute('data-highlighted')) {
            delete codeElement.dataset.highlighted; // Remove the attribute
        }
        // --- End of addition ---
        hljs.highlightElement(codeElement); // Now highlight it
    }
  }
};

onMounted(async () => {
  await checkLoginStatus();

  if (isAuthenticated.value) {
    console.log("User is authenticated, fetching keys...");
    await fetchUserKeys();
    console.log('Finished fetching keys. Has valid key:', hasValidKey.value)
    if (!isLoadingKeys.value && !hasValidKey.value) {
      console.log('No valid keys found, trying to generate');
      await generateNewKey();
      console.log('finished attempt to generate new key')
    }
  } else {
    console.log('user is not authenticated on mount')
  }
  highlightCode();
});

// Re-apply highlighting after any component update
onUpdated(() => {
  highlightCode();
});


watch(isAuthenticated, async (loggedIn, wasLoggedIn) => {
  console.log("Authentication status changed", loggedIn)
  if(loggedIn && !wasLoggedIn) {
    console.log("User just logged in, fetching keys");
    await fetchUserKeys();
    console.log("Finished fetching keys after logging in: hasValidKey.value", hasValidKey.value)
    if(!isLoadingKeys.value && !hasValidKey.value) {
      console.log("no valid keys found after login, generating new one")
      await generateNewKey();
      console.log("finished generating new key");
    }
  } else if (!loggedIn && wasLoggedIn) {
    console.log("user just logged out, clearing keys")
    userKeys.value = []
    newlyGeneratedKey.value = null;
  }
});


</script>

<template>
  <div>
    <h1>intercebd</h1>
    <p><i>log, annotate and fine-tune your LLM API calls</i></p>

    <div v-if="isLoading">
      <p>Checking login status...</p>
    </div>

    <div v-else>
      <div v-if="isAuthenticated && user">
        <button @click="logout">Logout</button>
        <p><h2> ✔ step 1 - login</h2></p>
        <p>thank you for signing in to intercebd, this is all the data we have about you from google, nothing else</p>
        <pre>User Info: {{ JSON.stringify(user, null, 2) }}</pre>
        
        <hr>

        <div>
          <h2>{{ firstValidKey ? '✔' : '' }} step 2 - get intercept key to log your llm calls </h2>
          <button @click="generateNewKey" :disabled="isGeneratingKey">
            {{  isGeneratingKey ? 'Generating...' : 'Generate New Key' }}
          </button>

          <div v-if="isLoadingKeys">
            <p>loading existing intercept keys</p>
          </div>
          <div v-else-if="firstValidKey">
            <h3>this is one of your valid intercept keys</h3>
            <pre><code>{{ firstValidKey }}</code></pre>
          </div>
          <div v-else-if="userKeys.length > 0">
            <h3>you have some existing keys</h3>
            <li v-for="key in userKeys">
              <pre>some key {{ key }}</pre>
            </li>
          </div>
          <div v-else>
            <p>you have no intercept keys, this should not have happened, we are trying to generate one for you automatically. maybe try to click the generate button.</p>
          </div>

          <p>the purpose of the intercept key is to allow you to log the LLM calls from a specific place in your code. in that specific place in the code you want the llm to behave a certain way so you want to annotate its behavior and want it to be robust in that specific context</p>
        </div>
        
        <hr>

        <div>
          <h2>step 3 - change your llm call code to use intercebd</h2>
          <p>
            intercebd is open source and you can host it yourself and share no data with anyone.
            if you don't host it yourself, you can use the saas version that
            you are trying now.
          </p>
          <p>
            in the saas version you will use your own openai/openrouter api keys,
            so intercebd recommends you generate a new api keys for trying out intercebd instead
            of entrusting intercebd with your api keys
          </p>
          <p>
            the url for the llm endpoints should be changed to the intercebd url
          </p>
          <pre ref="codeBlockRef"><code class="language-python">
from openai import OpenAI
import os

client = OpenAI(
  base_url="{{ API_BASE_URL }}/v1",
)

completion = client.chat.completions.create(
  model="openai/gpt-4.1-nano",
  messages=[
    {
      "role": "user",
      "content": "{{ promptContent.replace('"', '\\"') }}"
    }
  ],
  # add extra header for your intercebd
  extra_headers={
    "x-intercept-key": "{{ firstValidKey ? firstValidKey.intercept_key : "YOUR_INTERCEPT_KEY" }}",
  },
)
</code></pre>
          <p>to feel a bit of when trying this example you can write what you want the user prompt to be in the text box below</p>
          <div>
            <label for="promptInput">edit Prompt:</label><br>
            <input type="text" id="promptInput" v-model="promptContent" style="width: 80%; margin-bottom: 10px; padding: 5px;">
          </div>
        </div>

        
      </div>

      <div v-else>
        <h2>step 1 - login to generate an intercept key</h2>
        <button @click="login">Login with Google</button>
        <hr>
        <h2>{{ firstValidKey ? '✔' : '' }} step 2 - get intercept key to log your llm calls </h2>
         
        
        <hr>
      </div>
    </div>
  </div>
</template>

<style>
/* i try to avoid all styling */
pre {
  overflow-x: auto;
  white-space: pre-wrap;      
  word-break: break-word;  
}
</style>