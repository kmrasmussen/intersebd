import requests
import os
import json

# Get the API key from environment variable
api_key = os.environ.get("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY environment variable not set.")

# API endpoint
url = "https://api.openai.com/v1/responses"

# Headers
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {api_key}"
}

# Data payload
data = {
    "model": "gpt-4.1-nano", # Using nano as in the previous python script example
    "input": [{"role": "user", "content": "and what is the double of that?"}],
    "previous_response_id": "resp_68021781a4308191a30f36a6656534710556cba830c77eb3",
    "tools": [
        {
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
        }
    ]
}

# Make the POST request
response = requests.post(url, headers=headers, json=data)

# Print the response status code and content
print(f"Status Code: {response.status_code}")
try:
    print("Response JSON:")
    print(json.dumps(response.json(), indent=4))
except json.JSONDecodeError:
    print("Response Content (not JSON):")
    print(response.text)

# Example check similar to the previous script
if response.status_code == 200:
    response_data = response.json()
    if response_data.get("output"):
        first_output = response_data["output"][0]
        if first_output.get("type") == "function_call":
             print("\nokay wanted to use a tool")
        elif first_output.get("type") == "message":
             print("\nokay just a message")
        else:
             print(f"\nok don't know, unknown type: {first_output.get('type')}")
    else:
        print("\nok don't know, response output is empty or missing")
else:
    print("\nRequest failed.")

'''
curl -X 'POST' \
  'http://localhost:9003/agent-widgets/new_widget' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "user_id": "string",
  "origin": "string",
"tools": [
        {
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
                "additionalProperties": false
            }
        }
    ]
}'

{
  "user_id": "string",
  "origin": "null",
"tools": [
        {
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
                "additionalProperties": false
            }
        }
    ]
}


{
  "widget_id": "5d23f55b-9853-4080-a5c1-7fbe634fea89",
  "origin": "string",
  "tools": [
    {
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
        "additionalProperties": false
      }
    }
  ],
  "user_id": "string",
  "message": "Agent Widget created successfully."
}

''''