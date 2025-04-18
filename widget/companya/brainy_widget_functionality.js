const WIDGET_ID = "__WIDGET_ID_PLACEHOLDER__";
const API_ENDPOINT = "__API_ENDPOINT_PLACEHOLDER__";
const SESSION_STORAGE_KEY = 'brainyWidget_previousResponseId'; // Key for sessionStorage

// --- Initialize PREVIOUS_RESPONSE_ID from sessionStorage ---
let PREVIOUS_RESPONSE_ID = sessionStorage.getItem(SESSION_STORAGE_KEY) || null;
if (PREVIOUS_RESPONSE_ID) {
    console.log(`WIDGET: Initialized PREVIOUS_RESPONSE_ID from sessionStorage: ${PREVIOUS_RESPONSE_ID}`);
}

// Add more tool functions here as needed

// --- Response Handling ---
async function handleResponse(data) {
    console.log("WIDGET: Handling response:", data.id);
    const toolOutputs = [];
    let assistantTextMessage = null; // Variable to store the final text message

    if (data && data.output && Array.isArray(data.output)) {
        for (const outputItem of data.output) {
            // --- Tool Call Handling ---
            if (outputItem.type === "function_call" && outputItem.name) {
                console.log(`WIDGET: Detected function call: ${outputItem.name} (Call ID: ${outputItem.call_id})`);
                const toolFunctionName = `tool_${outputItem.name}`;
                if (typeof window[toolFunctionName] === 'function') {
                    let result = "Error: Tool execution failed.";
                    try {
                        const args = JSON.parse(outputItem.arguments);
                        console.log(`WIDGET: Calling adapter function ${toolFunctionName} with arguments:`, args);
                        const toolResult = window[toolFunctionName](args);
                        result = String(toolResult);
                        console.log(`WIDGET: Result from ${toolFunctionName}:`, result);
                    } catch (error) {
                        console.error(`WIDGET: Error executing or parsing args for ${outputItem.name}:`, error);
                        if (error instanceof Error) { result = `Error: ${error.message}`; }
                    }
                    toolOutputs.push({ type: "function_call_output", call_id: outputItem.call_id, output: result });
                } else {
                    console.warn(`WIDGET: Adapter function '${toolFunctionName}' not found.`);
                    toolOutputs.push({ type: "function_call_output", call_id: outputItem.call_id, output: `Error: Adapter function '${toolFunctionName}' is not implemented.` });
                }
            }
            // --- Assistant Message Handling ---
            else if (outputItem.type === 'message' && outputItem.role === 'assistant' && Array.isArray(outputItem.content)) {
                 // Find the first text content part - CORRECTED TYPE
                 const textContent = outputItem.content.find(contentPart => contentPart.type === 'output_text'); // <--- FIX HERE
                 if (textContent && typeof textContent.text === 'string') { // Check if text exists and is a string
                    assistantTextMessage = textContent.text; // Store the message
                    console.log("WIDGET: Received assistant text message:", assistantTextMessage);
                 } else {
                    console.log("WIDGET: Found assistant message but no 'output_text' content part with text.");
                 }
            }
            // --- Deprecated Text Completion Handling ---
            else if (outputItem.type === "text_completion") {
                 console.log("WIDGET: Received text completion (legacy?):", outputItem.text);
                 if (!assistantTextMessage) { // Only use if no message type found
                    assistantTextMessage = outputItem.text;
                 }
            } else {
                console.log("WIDGET: Received unhandled output item type:", outputItem.type, outputItem);
            }
        }

        // --- Send Tool Outputs Back (If Any) ---
        if (toolOutputs.length > 0) {
            console.log("WIDGET: Collected tool outputs, sending back to API:", toolOutputs);
            await sendMessage(toolOutputs, data.id); // Pass response ID explicitly
        }
        // --- Display Final Assistant Message (If No Tool Outputs Were Sent) ---
        else if (assistantTextMessage !== null) {
             console.log("WIDGET: Displaying final assistant message.");
             // Check if a custom handler exists
             if (typeof window.handleAssistantResponse === 'function') {
                 console.log("WIDGET: Calling custom handleAssistantResponse.");
                 try {
                    window.handleAssistantResponse(assistantTextMessage);
                 } catch (error) {
                    console.error("WIDGET: Error in custom handleAssistantResponse:", error);
                    // Fallback to alert if custom handler fails
                    alert("Error in custom handler. Response:\n" + assistantTextMessage);
                 }
             } else {
                 // Default behavior: Use alert()
                 console.log("WIDGET: No custom handleAssistantResponse found, using default alert.");
                 alert(assistantTextMessage);
             }
        } else if (toolOutputs.length === 0) {
            console.log("WIDGET: No tool outputs generated and no assistant text message found in response.");
        }

    } else {
        console.log("WIDGET: Response data does not contain a valid 'output' array.");
    }
}


// --- Message Sending ---
async function sendMessage(inputContent, explicitPreviousResponseId = null) {
    let inputPayload;
    let logMessage;

    if (typeof inputContent === 'string') {
        logMessage = `WIDGET: Sending user message: ${inputContent}`;
        inputPayload = [{"role": "user", "content": inputContent}];
    } else if (Array.isArray(inputContent)) {
        logMessage = "WIDGET: Sending tool outputs";
        inputPayload = inputContent;
    } else {
        console.error("WIDGET: Invalid input type for sendMessage:", inputContent);
        return;
    }

    console.log(logMessage);

    const payload = {
        widget_id: WIDGET_ID,
        input: inputPayload,
        model: "gpt-4.1-nano" // Optional: Add if you want to specify the model
    };

    // --- Use explicit ID if provided, otherwise use the global/session one ---
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
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        console.log("WIDGET: API Response:", data);

        if (data && data.id) {
            // --- Update global variable AND sessionStorage ---
            PREVIOUS_RESPONSE_ID = data.id;
            sessionStorage.setItem(SESSION_STORAGE_KEY, PREVIOUS_RESPONSE_ID);
            console.log(`Updated PREVIOUS_RESPONSE_ID to: ${PREVIOUS_RESPONSE_ID} (and saved to sessionStorage)`);
        } else {
             console.warn("Response did not contain an 'id'. PREVIOUS_RESPONSE_ID not updated.");
             // --- Consider clearing sessionStorage if the conversation breaks ---
             // sessionStorage.removeItem(SESSION_STORAGE_KEY);
             // PREVIOUS_RESPONSE_ID = null;
        }

        await handleResponse(data);

    } catch (error) {
        console.error('WIDGET: Error sending message/tool outputs:', error);
        // --- Consider clearing sessionStorage on major errors ---
        // sessionStorage.removeItem(SESSION_STORAGE_KEY);
        // PREVIOUS_RESPONSE_ID = null;
    }
}

// --- Global Access ---
window.sendMessage = sendMessage;

// --- Function to clear conversation state ---
window.clearWidgetConversation = function() {
    console.log("WIDGET: Clearing conversation state (PREVIOUS_RESPONSE_ID and sessionStorage).");
    PREVIOUS_RESPONSE_ID = null;
    sessionStorage.removeItem(SESSION_STORAGE_KEY);
};

console.log("Core Widget logic loaded.");

