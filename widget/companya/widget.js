const WIDGET_ID = "86bc07f1-1400-4fc6-8290-6444e97af4fc"; // Make sure this is the correct ID for the 'null' origin widget
const API_ENDPOINT = 'http://localhost:9003/cors-anywhere/agent_widget_request'; // Use the mounted path from main.py
let PREVIOUS_RESPONSE_ID = null; // Set to null if you don't want to use a previous response

// --- Tool Implementations ---
// Define functions that match the names provided in the tool configuration
// These functions will be called when the API response includes a function_call

function tool_get_weather(args) {
  // Expects args to be an object like { location: "City, Country" }
  if (args && args.location) {
    console.log(`TOOL EXECUTING: tool_getWeather for location: ${args.location}`);
    return "The weather is sunny";
    // In a real scenario, you might make another API call here
    // For now, just log it.
    // You might return a value or trigger another action based on the result.
  } else {
    console.error("tool_getWeather called without valid location argument:", args);
    throw new Error("Invalid arguments for tool_getWeather");
  }
}

// Add more tool functions here as needed, e.g., tool_addItem(args), tool_deleteItem(args)
// Make sure the function names start with "tool_" and match the 'name' in the tool definition.

// --- Response Handling ---

async function handleResponse(data) {
    console.log("Handling response:", data.id);

    if (data && data.output && Array.isArray(data.output)) {
        // Iterate through all outputs in the response (handles parallel tool calls)
        for (const outputItem of data.output) {
            if (outputItem.type === "function_call" && outputItem.name) {
                console.log(`Detected function call: ${outputItem.name}`);

                // Construct the expected tool function name
                const toolFunctionName = `tool_${outputItem.name}`;

                // Check if a corresponding tool function exists globally (or within this scope)
                if (typeof window[toolFunctionName] === 'function') {
                    try {
                        // Parse the arguments string into a JavaScript object
                        const args = JSON.parse(outputItem.arguments);
                        console.log(`Calling ${toolFunctionName} with arguments:`, args);

                        // Call the tool function with the parsed arguments
                        // Use 'await' if your tool functions are async
                        window[toolFunctionName](args);

                    } catch (parseError) {
                        console.error(`Error parsing arguments for ${outputItem.name}:`, parseError);
                        console.error("Arguments string:", outputItem.arguments);
                    }
                } else {
                    console.warn(`Tool function '${toolFunctionName}' not found.`);
                }
            } else if (outputItem.type === "text_completion") {
                 // Handle text responses if needed
                 console.log("Received text completion:", outputItem.text);
                 // You might display this text to the user
            } else {
                console.log("Received output item of type:", outputItem.type, outputItem);
            }
        }
    } else {
        console.log("Response data does not contain a valid 'output' array.");
    }
}


// --- Message Sending ---

async function sendMessage(userMessage) {
    console.log(`Sending message: ${userMessage}`);

    const payload = {
        widget_id: WIDGET_ID,
        input: [{"role": "user", "content": userMessage}],
        model: "gpt-4.1-nano" // Optional: Add if you want to specify the model
    };

    if (PREVIOUS_RESPONSE_ID) {
      payload.previous_response_id = PREVIOUS_RESPONSE_ID;
      console.log(`Including previous_response_id: ${PREVIOUS_RESPONSE_ID}`);
    } else {
        console.log("No previous_response_id to include.");
    }


    try {
        const response = await fetch(API_ENDPOINT, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'accept': 'application/json' // Good practice to include accept header
            },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            const errorBody = await response.text();
            console.error(`HTTP Error: ${response.status} ${response.statusText}`);
            console.error("Error details:", errorBody);
            // PREVIOUS_RESPONSE_ID = null; // Reset on error?
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        console.log("API Response:", data);

        if (data && data.id) {
            PREVIOUS_RESPONSE_ID = data.id; // Update the previous response ID
            console.log(`Updated PREVIOUS_RESPONSE_ID: ${PREVIOUS_RESPONSE_ID}`);
            // Call the handler function AFTER updating the ID
            await handleResponse(data); // Use await if handleResponse becomes async
        } else {
             console.warn("Response did not contain an 'id'. PREVIOUS_RESPONSE_ID not updated.");
             // PREVIOUS_RESPONSE_ID = null; // Optionally reset
             // Still try to handle the response even if ID is missing?
             await handleResponse(data);
        }

    } catch (error) {
        console.error('Error sending message:', error);
        // PREVIOUS_RESPONSE_ID = null; // Reset on fetch error?
    }
}

// --- Global Access ---
// Make tool functions and sendMessage globally accessible if needed
//window.tool_get_weather = tool_get_weather;
//window.sendMessage = sendMessage;

// Example usage:
// sendMessage("What's the weather like in Sofia and Plovdiv?");

