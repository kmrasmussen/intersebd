const WIDGET_ID = "9db28cfe-77a4-496a-af35-5342ce9a6004"; // Make sure this is the correct ID for the 'null' origin widget
const API_ENDPOINT = 'http://localhost:9003/cors-anywhere/agent_widget_request'; // Use the mounted path from main.py
let PREVIOUS_RESPONSE_ID = null; // Stores the ID of the *last successful response*

// Add more tool functions here as needed

// --- Response Handling ---

async function handleResponse(data) {
    console.log("Handling response:", data.id);
    const toolOutputs = []; // Array to collect results from tool calls

    if (data && data.output && Array.isArray(data.output)) {
        // Iterate through all outputs in the response
        for (const outputItem of data.output) {
            if (outputItem.type === "function_call" && outputItem.name) {
                console.log(`Detected function call: ${outputItem.name} (Call ID: ${outputItem.call_id})`);

                const toolFunctionName = `tool_${outputItem.name}`;

                if (typeof window[toolFunctionName] === 'function') {
                    let result = "Error: Tool execution failed."; // Default error result
                    try {
                        const args = JSON.parse(outputItem.arguments);
                        console.log(`Calling ${toolFunctionName} with arguments:`, args);

                        // Call the tool function and get the result
                        // Use 'await' if your tool functions are async
                        const toolResult = window[toolFunctionName](args);
                        result = String(toolResult); // Ensure the result is a string

                        console.log(`Result from ${toolFunctionName}:`, result);

                    } catch (error) {
                        console.error(`Error executing or parsing args for ${outputItem.name}:`, error);
                        console.error("Arguments string:", outputItem.arguments);
                        if (error instanceof Error) {
                            result = `Error: ${error.message}`;
                        }
                    }
                    // Add the result to our outputs list, linked by call_id
                    toolOutputs.push({
                        type: "function_call_output",
                        call_id: outputItem.call_id,
                        output: result
                    });

                } else {
                    console.warn(`Tool function '${toolFunctionName}' not found.`);
                    // Optionally send back an error result if the function is missing
                    toolOutputs.push({
                        type: "function_call_output",
                        call_id: outputItem.call_id,
                        output: `Error: Tool function '${toolFunctionName}' is not implemented.`
                    });
                }
            } else if (outputItem.type === "text_completion") {
                 console.log("Received text completion:", outputItem.text);
                 // Display this text to the user (e.g., append to chat)
                 // Example: document.getElementById('responseArea').innerText += outputItem.text + '\n';
            } else {
                console.log("Received output item of type:", outputItem.type, outputItem);
            }
        }

        // --- Send Tool Outputs Back ---
        if (toolOutputs.length > 0) {
            console.log("Collected tool outputs, sending back to API:", toolOutputs);
            // Send the collected tool outputs back, using the ID of the response
            // that requested these tool calls as the previous_response_id.
            await sendMessage(toolOutputs, data.id);
        }

    } else {
        console.log("Response data does not contain a valid 'output' array.");
    }
}


// --- Message Sending ---
// Modified to accept either a user message string or an array of tool outputs
async function sendMessage(inputContent, explicitPreviousResponseId = null) {

    let inputPayload;
    let logMessage;

    if (typeof inputContent === 'string') {
        logMessage = `Sending user message: ${inputContent}`;
        inputPayload = [{"role": "user", "content": inputContent}];
    } else if (Array.isArray(inputContent)) {
        logMessage = "Sending tool outputs";
        inputPayload = inputContent; // Assumes inputContent is already formatted correctly
    } else {
        console.error("Invalid input type for sendMessage:", inputContent);
        return; // Don't proceed if input is invalid
    }

    console.log(logMessage);

    const payload = {
        widget_id: WIDGET_ID,
        input: inputPayload,
        model: "gpt-4.1-nano" // Optional: Add if you want to specify the model
    };

    // Determine which previous_response_id to use
    const prevIdToSend = explicitPreviousResponseId || PREVIOUS_RESPONSE_ID;

    if (prevIdToSend) {
      payload.previous_response_id = prevIdToSend;
      console.log(`Including previous_response_id: ${prevIdToSend}`);
    } else {
        console.log("No previous_response_id to include.");
    }


    try {
        const response = await fetch(API_ENDPOINT, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'accept': 'application/json'
            },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            const errorBody = await response.text();
            console.error(`HTTP Error: ${response.status} ${response.statusText}`);
            console.error("Error details:", errorBody);
            // Decide if PREVIOUS_RESPONSE_ID should be reset on error
            // PREVIOUS_RESPONSE_ID = null;
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        console.log("API Response:", data);

        // IMPORTANT: Update the global PREVIOUS_RESPONSE_ID with the ID of *this* response
        if (data && data.id) {
            PREVIOUS_RESPONSE_ID = data.id;
            console.log(`Updated global PREVIOUS_RESPONSE_ID to: ${PREVIOUS_RESPONSE_ID}`);
        } else {
             console.warn("Response did not contain an 'id'. Global PREVIOUS_RESPONSE_ID not updated.");
             // Optionally reset if ID is missing?
             // PREVIOUS_RESPONSE_ID = null;
        }

        // Handle the response (which might trigger more tool calls or give final text)
        await handleResponse(data);

    } catch (error) {
        console.error('Error sending message/tool outputs:', error);
        // Decide if PREVIOUS_RESPONSE_ID should be reset on fetch error
        // PREVIOUS_RESPONSE_ID = null;
    }
}

// --- Global Access ---
// Make tool functions and sendMessage globally accessible if needed
window.sendMessage = sendMessage;

console.log("Core Widget logic loaded.");
// Example usage:
// sendMessage("What's the weather like in Sofia?"); // Triggers tool call
// -> handleResponse detects tool call, executes tool_get_weather
// -> handleResponse calls sendMessage again with the tool output
// -> handleResponse gets the final text response

