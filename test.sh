curl http://localhost:9003/v1/responses \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "x-intercept-key: 8e12655d-3df2-4c60-82ac-fd0fd71f0a4e" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o-mini",
    "input": [
      {
        "role": "system",
        "content": "You are a helpful math tutor. Guide the user through the solution step by step."
      },
      {
        "role": "user",
        "content": "how can I solve 8x + 7 = -23"
      }
    ],
    "text": {
      "format": {
        "type": "json_schema",
        "name": "math_reasoning",
        "schema": {
          "type": "object",
          "properties": {
            "steps": {
              "type": "array",
              "items": {
                "type": "object",
                "properties": {
                  "explanation": { "type": "string" },
                  "output": { "type": "string" }
                },
                "required": ["explanation", "output"],
                "additionalProperties": false
              }
            },
            "final_answer": { "type": "string" }
          },
          "required": ["steps", "final_answer"],
          "additionalProperties": false
        },
        "strict": true
      }
    }
  }'

curl -X POST https://openrouter.ai/api/v1/chat/completions \
     -H "Authorization: Bearer $OPENROUTER_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{
  "model": "openai/gpt-4o-mini",
  "messages": [
    {
      "role": "user",
      "content": "What is 2+2?"
    }
  ]
}'

curl -X POST http://localhost:9003/v1/chat/completions \
     -H "Authorization: Bearer $OPENROUTER_API_KEY" \
     -H "x-intercept-key: 8e12655d-3df2-4c60-82ac-fd0fd71f0a4e" \
     -H "Content-Type: application/json" \
     -d '{
  "model": "openai/gpt-4o-mini",
  "messages": [
    {
      "role": "user",
      "content": "What is 2+2?"
    }
  ]
}'

curl -X POST https://openrouter.ai/api/v1/chat/completions \
     -H "Authorization: Bearer $OPENROUTER_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{
  "model": "openai/gpt-4.1-nano",
  "messages": [
    {
      "role": "user",
      "content": "What books did jordan peterson write?"
    }
  ],
  "tools":[
  {
    "type": "function",
    "function": {
      "name": "search_gutenberg_books",
      "description": "Search for books in the Project Gutenberg library based on specified search terms",
      "parameters": {
        "type": "object",
        "properties": {
          "search_terms": {
            "type": "array",
            "items": {
              "type": "string"
            },
            "description": "List of search terms to find books in the Gutenberg library (e.g. ['dickens', 'great'] to search for books by Dickens with 'great' in the title)"
          }
        },
        "required": ["search_terms"]
      }
    }
  }
]
}'

curl -X POST http://localhost:9003/v1/chat/completions/rater/notifications \
  -H Content-Type: application/json \
  -d '{
      "rater_id": "sdlkfjdsafraterid",
      "content": "dsflksdfcontent",
      "completion_response_id": "gen-1744568518-ZXQp4E8aRlRb5alaF6zR"
  ]
}'