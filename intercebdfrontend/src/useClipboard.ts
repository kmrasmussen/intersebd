import { ref } from 'vue';
import type { Ref } from 'vue'; 
// No longer need 'Ref' type import here

export function useClipboard() {
  // State refs remain the same
  const copiedCurl = ref(false);
  const copiedPython = ref(false);
  const copiedJs = ref(false);

  // Base function to write to clipboard (remains the same)
  async function copyCode(textToCopy: string): Promise<boolean> {
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

  // Modified handler function - takes an ID instead of a Ref
  async function handleCopyClick(textToCopy: string, id: 'curl' | 'python' | 'js') {
    if (await copyCode(textToCopy)) {
      // Update the correct state based on the ID
      let targetRef: Ref<boolean> | null = null;
      if (id === 'curl') {
        targetRef = copiedCurl;
      } else if (id === 'python') {
        targetRef = copiedPython;
      } else if (id === 'js') {
        targetRef = copiedJs;
      }

      if (targetRef) {
        targetRef.value = true;
        setTimeout(() => {
          // Check again inside timeout just to be safe
          if (targetRef) {
             targetRef.value = false;
          }
        }, 2000);
      } else {
        console.error(`Invalid ID passed to handleCopyClick: ${id}`);
      }
    }
  }

  // Return the state refs and the modified handler function
  return {
    copiedCurl,
    copiedPython,
    copiedJs,
    handleCopyClick
  };
}