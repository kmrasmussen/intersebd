<script setup lang="ts">
import { computed, ref, type PropType } from 'vue';
import { useAnnotation } from '../useAnnotation';
import type { AnnotatableItemData } from '../types';
// Import the AnnotationResponse type if it's not globally available
import type { AnnotationResponse } from '../useAnnotation'; // Adjust path if needed

// --- Props ---
const props = defineProps({
  item: {
    type: Object as PropType<AnnotatableItemData>,
    required: true
  },
  annotationTargetId: {
    type: String,
    required: true
  },
  interceptKey: {
    type: String as PropType<string | null>,
    required: true
  }
});

// --- Composables ---
const keyRef = computed(() => props.interceptKey);
// Destructure ALL relevant state and functions from useAnnotation
const {
  // Create
  createAnnotationLoading, // Renamed
  createAnnotationError,   // Renamed
  createAnnotationSuccess, // Renamed
  annotateRewardOne,
  // Fetch
  fetchedAnnotations,
  fetchAnnotationsLoading,
  fetchAnnotationsError,
  fetchAnnotationsForTarget
} = useAnnotation(keyRef);

// --- State ---
const showRawData = ref(false);
const showAnnotations = ref(false); // State to toggle annotation list visibility

// --- Computed ---
// Computed ref for the annotations specific to this item's target ID
const currentAnnotations = computed<AnnotationResponse[]>(() => {
  return fetchedAnnotations.value[props.annotationTargetId] || [];
});
// Computed ref for the loading state specific to this item's target ID
const isFetchingAnnotations = computed<boolean>(() => {
  return fetchAnnotationsLoading.value[props.annotationTargetId] || false;
});
// Computed ref for the error state specific to this item's target ID
const fetchAnnotationsErrorMessage = computed<string | null>(() => {
  return fetchAnnotationsError.value[props.annotationTargetId] || null;
});

// --- Methods ---
const handleAnnotateClick = async () => { // <-- Make the handler async
  const uiStateKey = props.item.id;
  // Await the annotation process
  await annotateRewardOne(uiStateKey, props.annotationTargetId);

  // Check if the annotation was successful before refreshing
  // Note: createAnnotationSuccess state might update slightly after the await,
  // so checking it directly might be tricky. A safer bet is to just refresh
  // if there wasn't an error during the await.
  // Alternatively, modify useAnnotation to return the success status from annotateRewardOne.
  // For now, let's refresh if the error state for this item is null.
  if (!createAnnotationError.value[uiStateKey]) {
      console.log(`Annotation successful (or no error reported), refreshing annotations for ${props.annotationTargetId}`);
      // Ensure the annotations section is visible after annotating
      showAnnotations.value = true;
      // Fetch the latest annotations
      fetchAnnotationsForTarget(props.annotationTargetId);
  }
};

const toggleRawData = () => {
  showRawData.value = !showRawData.value;
};

// Method to fetch annotations and toggle visibility
const handleFetchAnnotationsClick = () => {
  // Always fetch when clicked (to refresh)
  fetchAnnotationsForTarget(props.annotationTargetId);
  // Toggle visibility only if not already shown, or if fetching wasn't already in progress
  if (!showAnnotations.value || !isFetchingAnnotations.value) {
     showAnnotations.value = !showAnnotations.value;
  }
};

</script>

<template>
  <div class="annotatable-item">
    <!-- Display Content based on Kind -->
    <div v-if="props.item.kind === 'response'">
      <h5>Response Content:</h5>
      <pre><code>{{ props.item.choice_content || '(No content)' }}</code></pre>
      <small v-if="props.item.model">Model: {{ props.item.model }}</small>
      <small v-if="props.item.created"> | Created: {{ new Date(props.item.created * 1000).toLocaleString() }}</small>
    </div>
    <div v-else-if="props.item.kind === 'alternative'">
      <h5>Alternative Content:</h5>
      <pre><code>{{ props.item.alternative_content }}</code></pre>
      <small>Submitted: {{ new Date(props.item.created_at).toLocaleString() }}</small>
      <small v-if="props.item.rater_id"> | Rater: {{ props.item.rater_id }}</small>
    </div>

    <!-- Annotation Controls (Common) -->
    <div class="annotation-controls">
      <button
        @click="handleAnnotateClick"
        :disabled="createAnnotationLoading[props.item.id] || !interceptKey"
      >
        {{ createAnnotationLoading[props.item.id] ? 'Annotating...' : 'Annotate with reward 1 (New Comp)' }}
      </button>
      <span v-if="createAnnotationSuccess[props.item.id]" style="color: green; margin-left: 10px;">✓ Annotated!</span>
      <span v-if="createAnnotationError[props.item.id]" style="color: red; margin-left: 10px;">{{ createAnnotationError[props.item.id] }}</span>
    </div>

    <!-- Fetch Annotations Controls -->
    <div class="fetch-annotations-section">
      <button @click="handleFetchAnnotationsClick" class="fetch-annotations-button">
        {{ isFetchingAnnotations ? 'Fetching Annotations...' : (showAnnotations ? 'Refresh Annotations' : 'Show Annotations') }}
      </button>
      <span v-if="fetchAnnotationsErrorMessage" style="color: red; margin-left: 10px;">{{ fetchAnnotationsErrorMessage }}</span>
      <ul v-if="showAnnotations" class="annotations-list">
        <li v-for="annotation in currentAnnotations" :key="annotation.id">
          Reward: {{ annotation.reward ?? 'N/A' }}
          <small> | By: {{ annotation.rater_id ?? 'Unknown' }}</small>
          <small> | At: {{ new Date(annotation.timestamp).toLocaleString() }}</small>
          <!-- Optionally display metadata if it exists -->
          <!-- <pre v-if="annotation.annotation_metadata && Object.keys(annotation.annotation_metadata).length > 0"><code>{{ JSON.stringify(annotation.annotation_metadata, null, 2) }}</code></pre> -->
        </li>
      </ul>
    </div>

    <!-- Raw Data Toggle and Display -->
    <div class="raw-data-section">
      <button @click="toggleRawData" class="toggle-raw-button">
        {{ showRawData ? 'Hide Raw Data' : 'Show Raw Data' }}
      </button>
      <pre v-if="showRawData" class="raw-data-pre"><code>{{ JSON.stringify(props.item, null, 2) }}</code></pre>
    </div>
  </div>
</template>

<style scoped>
.annotatable-item {
  padding: 15px;
  border: 1px dashed blue; /* Dashed blue border to distinguish it */
  margin-top: 15px;
  margin-bottom: 15px;
  border-radius: 4px;
  background-color: #f0f8ff; /* Light blue background */
}
h5 {
  margin-top: 0;
  margin-bottom: 5px;
  color: #333;
}
pre {
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-all;
  background-color: #e8f4ff; /* Slightly darker blue background for pre */
  padding: 10px;
  border: 1px solid #cce0ff;
  border-radius: 4px;
  font-size: 0.9em;
  margin-top: 5px;
}
button {
  margin-top: 10px;
  margin-right: 5px;
  padding: 5px 10px;
  cursor: pointer;
  background-color: #add8e6; /* Light blue button */
  border: 1px solid #9acae6;
}
button:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}
small {
  font-size: 0.8em;
  color: #555;
  margin-right: 5px;
}
.annotation-controls {
  margin-top: 10px;
}
.fetch-annotations-section {
  margin-top: 15px;
  border-top: 1px solid #eee; /* Add a separator */
  padding-top: 10px;
}
.fetch-annotations-button {
  background-color: #eee;
  border: 1px solid #ddd;
  color: #333;
  font-size: 0.8em;
  padding: 3px 8px;
}
.annotations-list {
  margin-top: 10px;
  padding-left: 20px;
  list-style-type: disc;
}
.raw-data-section {
  margin-top: 15px;
  border-top: 1px solid #eee; /* Add a separator */
  padding-top: 10px;
}
.toggle-raw-button {
  background-color: #eee;
  border: 1px solid #ddd;
  color: #333;
  font-size: 0.8em;
  padding: 3px 8px;
}
.raw-data-pre {
  margin-top: 10px;
  background-color: #333; /* Dark background for raw data */
  color: #eee; /* Light text */
  border: 1px solid #555;
  font-size: 0.85em;
}
</style>