/**
 * Adapter function called by widget.js when the API requests 'add_item'.
 * This function bridges the gap to the application's actual addItem logic.
 * @param {object} args - Arguments provided by the API, e.g., { name: "Item Name", content: "Item Content" }
 * @returns {string} - A result message string to send back to the API.
 */
function tool_add_item(args) {
  // Validate arguments received from the API call
  if (args && args.name && args.content) {
    console.log(`ADAPTER: tool_add_item called with name: ${args.name}, content: ${args.content}`);
    try {
      // Check if the application's addItem function is available (globally in this case)
      if (typeof window.addItem === 'function') {
        // Call the application's addItem function
        window.addItem(args.name, args.content);
        // Return a success message for the API
        return `Successfully added item via adapter: ${args.name}`;
      } else {
        console.error("ADAPTER: window.addItem function not found!");
        return "Error: Application's addItem function is not available.";
      }
    } catch (error) {
      console.error("ADAPTER: Error calling window.addItem:", error);
      // Return an error message for the API
      return `Error executing application's addItem: ${error.message}`;
    }
  } else {
    console.error("ADAPTER: tool_add_item called without valid name/content arguments:", args);
    // Return an error message string for the API
    return "Error: Name and/or content arguments missing in tool call.";
  }
}

/**
 * Adapter function called by widget.js when the API requests 'delete_item'.
 * This function bridges the gap to the application's actual deleteItem logic.
 * @param {object} args - Arguments provided by the API, e.g., { name: "Item Name" }
 * @returns {string} - A result message string to send back to the API.
 */
function tool_delete_item(args) {
  // Validate arguments
  if (args && args.name) {
    console.log(`ADAPTER: tool_delete_item called with name: ${args.name}`);
    try {
      // Check if the application's deleteItem function is available
      if (typeof window.deleteItem === 'function') {
        // Call the application's deleteItem function
        window.deleteItem(args.name);
        // Return a success message for the API
        return `Successfully deleted item via adapter: ${args.name}`;
      } else {
        console.error("ADAPTER: window.deleteItem function not found!");
        return "Error: Application's deleteItem function is not available.";
      }
    } catch (error) {
      console.error("ADAPTER: Error calling window.deleteItem:", error);
      // Return an error message for the API
      return `Error executing application's deleteItem: ${error.message}`;
    }
  } else {
    console.error("ADAPTER: tool_delete_item called without valid name argument:", args);
    // Return an error message string for the API
    return "Error: Name argument missing in tool call.";
  }
}

// --- Make Adapter Functions Globally Available ---
// widget.js needs to be able to find these tool_ functions.
// Ensure this script is loaded *before* widget.js or make them available
// in a way widget.js can access them (global scope is simplest here).
window.tool_add_item = tool_add_item;
window.tool_delete_item = tool_delete_item;

// Example for tool_get_weather (if you want it handled by the adapter too)
function tool_get_weather(args) {
  // This adapter function provides the implementation for get_weather
  if (args && args.location) {
    console.log(`ADAPTER: tool_get_weather for location: ${args.location}`);
    const weatherData = {
        "Sofia, Bulgaria": "Sunny, 25°C (Adapter)",
        "Plovdiv, Bulgaria": "Cloudy, 22°C (Adapter)",
        "Sofia": "Sunny, 25°C (Adapter)",
        "Plovdiv": "Cloudy, 22°C (Adapter)"
    };
    return weatherData[args.location] || `Weather data not available via adapter for ${args.location}`;
  } else {
    console.error("ADAPTER: tool_get_weather called without valid location argument:", args);
    return "Error: Location argument missing for get_weather (Adapter).";
  }
}
window.tool_get_weather = tool_get_weather;

/**
 * OPTIONAL: Custom handler for displaying the assistant's final text response.
 * If this function exists (uncommented and assigned to window), widget.js will call it.
 * Otherwise, widget.js will use a default alert().
 * @param {string} messageText - The text content from the assistant's message.
 */
function handleAssistantResponse(messageText) {
  console.log("ADAPTER: handleAssistantResponse received:", messageText);

  // Example: Append the message to a specific div on the page
  // const chatArea = document.getElementById('chatOutputArea'); // Assuming you have such an element
  // if (chatArea) {
  //   const messageElement = document.createElement('p');
  //   messageElement.textContent = "Assistant: " + messageText;
  //   chatArea.appendChild(messageElement);
  //   chatArea.scrollTop = chatArea.scrollHeight; // Scroll to bottom
  // } else {
  //   // Fallback if the target element doesn't exist
  //   alert("Assistant: " + messageText);
  // }

  // Or just use alert as a starting point:
  alert("Assistant says: " + messageText);
}
window.handleAssistantResponse = handleAssistantResponse;

console.log("Widget Adapter loaded.");