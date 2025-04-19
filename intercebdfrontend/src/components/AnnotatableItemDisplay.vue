<script setup lang="ts">
import { computed, ref, type PropType } from 'vue';
import { useAnnotation } from '../useAnnotation';
import type { AnnotatableItemData } from '../types';
import type { AnnotationResponse } from '../useAnnotation';

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
  fetchAnnotationsForTarget,
  // Delete
  deleteAnnotationLoading, 
  deleteAnnotationError, 
  deleteAnnotation // <-- Add delete parts
} = useAnnotation(keyRef);

// --- State ---
const showRawData = ref(false);
const showAnnotations = ref(false); // State to toggle annotation list visibility
const isCollapsed = ref(true); // <-- Add state for collapsing, default to collapsed

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

// NEW: Computed property for the summary line
const summaryContent = computed(() => {
  const maxLen = 80; // Max length for summary
  let content = '';
  if (props.item.kind === 'response') {
    content = props.item.choice_content || '(No content)';
  } else if (props.item.kind === 'alternative') {
    content = props.item.alternative_content || '(No content)';
  }
  return content.length > maxLen ? content.substring(0, maxLen) + '...' : content;
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

// NEW: Method to toggle collapsed state
const toggleCollapse = () => {
  isCollapsed.value = !isCollapsed.value;
};

// NEW: Method to handle annotation deletion
const handleDeleteAnnotation = async (annotationId: string) => {
  console.log(`[handleDeleteAnnotation] Clicked delete for annotation ID: ${annotationId}`); // <-- ADD THIS LOG

  // Optional: Confirm before deleting
  // if (!confirm(`Are you sure you want to delete annotation ${annotationId}?`)) {
  //   return;
  // }

  const success = await deleteAnnotation(annotationId);

  if (success) {
    // Refresh the list for this item after successful deletion
    console.log(`[handleDeleteAnnotation] Deletion successful for ${annotationId}, refreshing annotations for target ${props.annotationTargetId}`);
    fetchAnnotationsForTarget(props.annotationTargetId);
  } else {
    // Error is handled via deleteAnnotationError state
    console.error(`[handleDeleteAnnotation] Deletion failed for ${annotationId} (check composable logs/state)`); // <-- Added context
  }
};

</script>

<template>
  <div class="annotatable-item" :class="{ collapsed: isCollapsed }">

    <!-- Header/Summary Area (Always Visible, Clickable) -->
    <div class="item-header" @click="toggleCollapse">
      <span class="collapse-toggle">{{ isCollapsed ? '►' : '▼' }}</span>
      <span v-if="props.item.kind === 'response'">
        <strong>Response:</strong> <span class="summary-text">{{ summaryContent }}</span>
      </span>
      <span v-else-if="props.item.kind === 'alternative'">
        <strong>Alternative:</strong> <span class="summary-text">{{ summaryContent }}</span>
      </span>
    </div>

    <!-- Collapsible Content Area -->
    <div v-if="!isCollapsed" class="item-content">

      <!-- Original Content Display -->
      <div v-if="props.item.kind === 'response'">
        <pre><code>{{ props.item.choice_content || '(No content)' }}</code></pre>
        <small v-if="props.item.model">Model: {{ props.item.model }}</small>
        <small v-if="props.item.created"> | Created: {{ new Date(props.item.created * 1000).toLocaleString() }}</small>
      </div>
      <div v-else-if="props.item.kind === 'alternative'">
        <pre><code>{{ props.item.alternative_content }}</code></pre>
        <small>Submitted: {{ new Date(props.item.created_at).toLocaleString() }}</small>
        <small v-if="props.item.rater_id"> | Rater: {{ props.item.rater_id }}</small>
      </div>

      <!-- Action Buttons Row -->
      <div class="action-buttons-row">
        <div class="annotation-controls button-group">
          <button
            @click="handleAnnotateClick"
            :disabled="createAnnotationLoading[props.item.id] || !interceptKey"
          >
            {{ createAnnotationLoading[props.item.id] ? 'Annotating...' : 'Annotate with reward 1' }}
          </button>
          <span v-if="createAnnotationSuccess[props.item.id]" style="color: green; margin-left: 5px;">✓</span>
          <span v-if="createAnnotationError[props.item.id]" style="color: red; margin-left: 5px; cursor: help;" :title="createAnnotationError[props.item.id] ?? undefined">Error!</span>
        </div>

        <div class="fetch-annotations-section button-group">
          <button @click="handleFetchAnnotationsClick" class="fetch-annotations-button">
            {{ isFetchingAnnotations ? 'Fetching...' : (showAnnotations ? 'Hide/Refresh Annotations' : 'Show Annotations') }}
          </button>
          <span v-if="fetchAnnotationsErrorMessage" style="color: red; margin-left: 5px; cursor: help;" :title="fetchAnnotationsErrorMessage">Error!</span>
        </div>

        <div class="raw-data-section button-group">
          <button @click="toggleRawData" class="toggle-raw-button">
            {{ showRawData ? 'Hide Raw Data' : 'Show Raw Data' }}
          </button>
        </div>
      </div>

      <!-- Display Annotations List (Conditional) -->
      <div v-if="showAnnotations" class="annotations-display-area">
        <span v-if="isFetchingAnnotations" style="font-style: italic; color: #555;">Loading annotations...</span>
        <ul v-else-if="currentAnnotations.length > 0" class="annotations-list">
          <li v-for="annotation in currentAnnotations" :key="annotation.id">
            Reward: {{ annotation.reward ?? 'N/A' }}
            <small> | By: {{ annotation.rater_id ?? 'Unknown' }}</small>
            <small> | At: {{ new Date(annotation.timestamp).toLocaleString() }}</small>

            <!-- Modified Delete Button Area -->
            <span
              class="delete-control"
              @click="handleDeleteAnnotation(annotation.id)"
              :class="{ disabled: deleteAnnotationLoading[annotation.id] }"
              title="Delete this annotation"
            >
              <small> | </small>
              <button
                tabindex="-1"
                :disabled="deleteAnnotationLoading[annotation.id]"
                class="delete-annotation-btn"
                aria-hidden="true"
              >
                {{ deleteAnnotationLoading[annotation.id] ? '...' : 'X' }}
              </button>
              <span class="delete-text">delete</span>
              <span v-if="deleteAnnotationError[annotation.id]" class="delete-error" :title="deleteAnnotationError[annotation.id] ?? undefined">
                ⚠️ Error
              </span>
            </span>
          </li>
        </ul>
        <p v-else-if="!fetchAnnotationsErrorMessage" style="font-style: italic; color: #555;">No annotations found.</p>
      </div>

      <!-- Display Raw Data (Conditional) -->
      <div v-if="showRawData" class="raw-data-display-area">
        <pre class="raw-data-pre"><code>{{ JSON.stringify(props.item, null, 2) }}</code></pre>
      </div>

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
.annotatable-item.collapsed {
  cursor: pointer;
}
.item-header {
  display: flex;
  align-items: center;
  cursor: pointer;
  background-color: #e8f4ff; /* Slightly darker blue background for header */
  padding: 10px;
  border: 1px solid #cce0ff;
  border-radius: 4px;
}
.collapse-toggle {
  margin-right: 10px;
  font-size: 1.2em;
  color: #333;
}
.summary-text {
  font-size: 0.9em;
  color: #555;
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
  margin-top: 0;
  border-top: none;
  padding-top: 0;
}
.fetch-annotations-section {
  margin-top: 0;
  border-top: none;
  padding-top: 0;
}
.fetch-annotations-button {
  background-color: #eee;
  border: 1px solid #ddd;
  color: #333;
  font-size: 0.9em; /* Adjusted size slightly */
  padding: 4px 8px;
}
.annotations-list {
  margin-top: 5px; /* Space below loading/no annotations text */
  padding-left: 20px;
  list-style-type: disc;
}
.annotations-list li {
   margin-bottom: 3px;
   font-size: 0.9em;
   display: flex;
   align-items: baseline; /* Align text baselines */
   gap: 8px;
   flex-wrap: wrap; /* Allow wrapping if needed */
}
.raw-data-section {
  margin-top: 0;
  border-top: none;
  padding-top: 0;
}
.toggle-raw-button {
  background-color: #eee;
  border: 1px solid #ddd;
  color: #333;
  font-size: 0.9em; /* Adjusted size slightly */
  padding: 4px 8px;
}
.raw-data-pre {
  margin-top: 5px;
  background-color: #333; /* Dark background for raw data */
  color: #eee; /* Light text */
  border: 1px solid #555;
  font-size: 0.85em;
  padding: 8px;
  border-radius: 3px;
  max-height: 200px; /* Limit height */
  overflow-y: auto;
}
.action-buttons-row {
  display: flex;
  flex-wrap: wrap; /* Allow buttons to wrap on smaller screens */
  align-items: center; /* Align items vertically */
  gap: 15px; /* Space between button groups */
  margin-top: 15px; /* Space above the button row */
  padding-bottom: 10px; /* Space below the button row */
  border-bottom: 1px solid #e0f0ff; /* Optional separator */
  margin-bottom: 10px; /* Space above collapsible content */
}
.button-group {
  display: flex;
  align-items: center; /* Align button and status icon */
  gap: 5px; /* Space between button and status icon */
}
.annotations-display-area {
  margin-top: 10px; /* Space below the button row */
}
.raw-data-display-area {
  margin-top: 10px; /* Space below the button row */
}

/* NEW: Container for delete controls */
.delete-control {
  display: inline-flex; /* Keep items inline */
  align-items: center; /* Vertically center items */
  gap: 4px; /* Space between separator, button, text */
}

/* Adjust delete button styles */
.delete-annotation-btn {
  padding: 0px 4px; /* Minimal padding */
  font-size: 0.8em;
  line-height: 1;
  background-color: transparent; /* Make background transparent */
  border: 1px solid #ffaaaa; /* Keep border */
  color: #c00;
  cursor: pointer;
  border-radius: 3px;
  font-weight: bold; /* Make X bold */
  /* Remove inherited margins */
  margin-top: 0;
  margin-right: 0;
  margin-left: 0; /* Remove auto margin */
}
.delete-annotation-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.delete-annotation-btn:hover {
  background-color: #ffeeee; /* Slight background on hover */
}

/* NEW: Style for the "delete" text */
.delete-text {
  font-size: 0.8em;
  color: #cc0000; /* Match button color */
  cursor: pointer; /* Make text look clickable (optional) */
}
.delete-text:hover {
  text-decoration: underline;
}

.delete-error {
  color: #c00;
  font-size: 0.8em;
  font-weight: bold;
  cursor: help; 
  margin-left: 5px; /* Add space before error icon */
}

</style>