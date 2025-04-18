from openai import OpenAI
# It might be necessary to import the specific types if checking with isinstance
# from openai.types.beta.threads import ResponseFunctionToolCall, ResponseOutputMessage # Example import path, adjust if needed

client = OpenAI()

tools = [{
    "type": "function",
    "name": "get_weather",
    "description": "Get current temperature for a given location.",
    "parameters": {
        "type": "object",
        "properties": {
            "location": {
                "type": "string",
                "description": "City and country e.g. Bogotá, Colombia"
            }
        },
        "required": [
            "location"
        ],
        "additionalProperties": False
    }
}]

response = client.responses.create(
    model="gpt-4.1-nano",
    input=[{"role": "user", "content": "what is 2+2?"}],
    # input=[{"role": "user", "content": "what is the weather in Paris?"}], # Uncomment to test tool call
    tools=tools
)

print(response.output)

# Check the type of the first output item
if response.output:
    first_output = response.output[0]
    # Check based on the 'type' attribute observed in the output
    if hasattr(first_output, 'type'):
        if first_output.type == 'function_call':
            print("okay wanted to use a tool")
        elif first_output.type == 'message':
             print("okay just a message")
        else:
            print(f"ok don't know, unknown type: {first_output.type}")
    # Alternative: Check using isinstance (requires correct imports)
    # elif isinstance(first_output, ResponseFunctionToolCall):
    #     print("okay wanted to use a tool")
    # elif isinstance(first_output, ResponseOutputMessage):
    #     print("okay just a message")
    else:
        print(f"ok don't know, object type is {type(first_output)}")
else:
    print("ok don't know, response output is empty")