"use client"

import { useState } from "react"
import { RequestHeader } from "@/components/request-details/request-header"
import { RequestCard } from "@/components/request-details/request-card"
import { ResponseSection } from "@/components/request-details/response-section"
import { AlternativesSection } from "@/components/request-details/alternatives-section"
import { NewAlternativeForm } from "@/components/request-details/new-alternative-form"

// Mock data for a single request
const mockRequests = {
  "f3ef3f5e-09c2-4a30-82a2-ecf4f460a1d9": {
    id: "f3ef3f5e-09c2-4a30-82a2-ecf4f460a1d9",
    name: "What is 2+12?",
    pairNumber: 2,
    request: {
      id: "f3ef3f5e-09c2-4a30-82a2-ecf4f460a1d9",
      request_log_id: "d4d2a938-0e3f-46ba-8414-21d72ae8c807",
      intercept_key: "sk-intercept-v1-JHteQu40BvrlnOD4onvz0LZIpzBNv8t4qwMDO0hL3hSzCGw2kyHw",
      messages: [
        {
          role: "system",
          content: "You are a helpful assistant",
        },
        {
          role: "user",
          content: "What is 2+12?",
        },
      ],
      model: "openai/gpt-4.1-nano",
      response_format: null,
      request_timestamp: "2025-04-19T11:22:44.054152Z",
    },
    mainResponse: {
      id: "gen-1745061763-51UoTnHd5YbhmM8TMKK",
      content: "2 + 12 equals 14.",
      model: "openai/gpt-4.1-nano",
      created: "2025-04-19T14:22:43Z",
      annotations: [
        {
          reward: 1,
          by: "guest-rater",
          at: "2025-04-19T14:25:30Z",
        },
      ],
      metadata: {
        completion_id: "f3ef3f5e-09c2-4a30-82a2-ecf4f460a1d9",
        annotation_target_id: "3b550e5c-9fb0-419c-9739-8106fe0d019c",
        provider: "OpenAI",
        model: "openai/gpt-4.1-nano",
        prompt_tokens: 14,
        completion_tokens: 9,
        total_tokens: 23,
        choice_finish_reason: "stop",
        choice_role: "assistant",
        choice_content: "2 + 12 equals 14.",
      },
      is_json: false,
      obeys_schema: null,
    },
    alternativeResponses: [
      {
        id: "alt-1",
        content: "sdfsad",
        model: "openai/gpt-4.1-nano",
        created: "2025-04-19T14:25:40Z",
        annotations: [],
        is_json: false,
        obeys_schema: null,
      },
      {
        id: "alt-2",
        content: '{\n  "results": 14\n}',
        model: "openai/gpt-4.1-nano",
        created: "2025-04-19T14:50:44Z",
        annotations: [
          {
            reward: 1,
            by: "guest-rater",
            at: "2025-04-19T14:50:48Z",
          },
          {
            reward: 1,
            by: "guest-rater",
            at: "2025-04-19T14:50:49Z",
          },
        ],
        is_json: true,
        obeys_schema: false,
      },
      {
        id: "alt-2",
        content: '{\n  "result": 14\n}',
        model: "openai/gpt-4.1-nano",
        created: "2025-04-19T14:50:44Z",
        annotations: [
          {
            reward: 1,
            by: "guest-rater",
            at: "2025-04-19T14:50:48Z",
          },
          {
            reward: 1,
            by: "guest-rater",
            at: "2025-04-19T14:50:49Z",
          },
        ],
        is_json: true,
        obeys_schema: true,
      },
    ],
  },
  "a1b2c3d4-5e6f-7g8h-9i0j-klmno1p2q3r4": {
    id: "a1b2c3d4-5e6f-7g8h-9i0j-klmno1p2q3r4",
    name: "Multi-turn conversation",
    pairNumber: 3,
    request: {
      id: "a1b2c3d4-5e6f-7g8h-9i0j-klmno1p2q3r4",
      request_log_id: "e5f6g7h8-i9j0-k1l2-m3n4-o5p6q7r8s9t0",
      intercept_key: "sk-intercept-v1-KJteRu50CwsmoPE5pnwz1MZJqzCOw9u5rwNEP1iM4iTzDHx3lzIx",
      messages: [
        {
          role: "system",
          content: "You are a helpful assistant",
        },
        {
          role: "user",
          content: "What is 2+12?",
        },
        {
          role: "assistant",
          content: "It is 14.",
        },
        {
          role: "user",
          content: "What is the double of that?",
        },
      ],
      model: "openai/gpt-4.1-nano",
      response_format: null,
      request_timestamp: "2025-04-18T15:30:22.123456Z",
    },
    mainResponse: {
      id: "gen-1745061764-62VpUnIe6ZchnN9UNLM",
      content: "The double of 14 is 28.",
      model: "openai/gpt-4.1-nano",
      created: "2025-04-18T15:30:25Z",
      annotations: [],
      metadata: {
        completion_id: "a1b2c3d4-5e6f-7g8h-9i0j-klmno1p2q3r4",
        annotation_target_id: "4c651f6d-0gc1-520d-0840-9217gf1e120d",
        provider: "OpenAI",
        model: "openai/gpt-4.1-nano",
        prompt_tokens: 32,
        completion_tokens: 7,
        total_tokens: 39,
        choice_finish_reason: "stop",
        choice_role: "assistant",
        choice_content: "The double of 14 is 28.",
      },
      is_json: false,
      obeys_schema: null,
    },
    alternativeResponses: [],
  },
  // Add a JSON example
  "json-example-id": {
    id: "json-example-id",
    name: "JSON Response Example",
    pairNumber: 4,
    request: {
      id: "json-example-id",
      request_log_id: "json-log-id",
      intercept_key: "sk-intercept-v1-json-example",
      messages: [
        {
          role: "system",
          content: "You are a helpful assistant that responds in JSON format.",
        },
        {
          role: "user",
          content: "Give me information about the planet Mars in JSON format.",
        },
      ],
      model: "openai/gpt-4.1-nano",
      response_format: { type: "json_object" },
      request_timestamp: "2025-04-20T10:15:30.123456Z",
    },
    mainResponse: {
      id: "json-response-1",
      content:
        '{\n  "planet": "Mars",\n  "diameter": "6,779 km",\n  "mass": "6.42 × 10^23 kg",\n  "gravity": "3.721 m/s²",\n  "day_length": "24.6 hours",\n  "year_length": "687 Earth days",\n  "moons": ["Phobos", "Deimos"],\n  "atmosphere": {\n    "composition": ["CO2", "Nitrogen", "Argon"],\n    "pressure": "0.006 atm"\n  }\n}',
      model: "openai/gpt-4.1-nano",
      created: "2025-04-20T10:15:35Z",
      annotations: [
        {
          reward: 1,
          by: "json-validator",
          at: "2025-04-20T10:15:40Z",
        },
      ],
      metadata: {
        completion_id: "json-completion-id",
        annotation_target_id: "json-target-id",
        provider: "OpenAI",
        model: "openai/gpt-4.1-nano",
        prompt_tokens: 25,
        completion_tokens: 18,
        total_tokens: 43,
        choice_finish_reason: "stop",
        choice_role: "assistant",
      },
      is_json: true,
      obeys_schema: true,
    },
    alternativeResponses: [
      {
        id: "json-alt-1",
        content:
          '{\n  "name": "Mars",\n  "type": "Terrestrial planet",\n  "distance_from_sun": "227.9 million km",\n  "features": ["Red planet", "Olympus Mons", "Valles Marineris"]\n}',
        model: "openai/gpt-4.1-nano",
        created: "2025-04-20T10:16:00Z",
        annotations: [],
        is_json: true,
        obeys_schema: true,
      },
      {
        id: "json-alt-2",
        content: '{\n  "planet": "Mars"\n  "color": "Red",\n  "position": "Fourth planet from the Sun"\n}',
        model: "openai/gpt-4.1-nano",
        created: "2025-04-20T10:16:30Z",
        annotations: [],
        is_json: true,
        obeys_schema: false,
      },
    ],
  },
}

export function RequestDetails({ id }: { id: string }) {
  // Remove <RequestData> and let TypeScript infer the correct union type
  const [request] = useState(
    mockRequests[id as keyof typeof mockRequests] || mockRequests["f3ef3f5e-09c2-4a30-82a2-ecf4f460a1d9"]
  )
  const [showAlternatives, setShowAlternatives] = useState(true)
  const [newAlternative, setNewAlternative] = useState("")

  return (
    <div className="space-y-6">
      <RequestHeader id={request.id} name={request.name} />

      <div className="mb-6">
        <h3 className="font-medium mb-2">Request:</h3>
        <RequestCard request={request.request} />
      </div>

      <div className="mb-6">
        <h3 className="font-medium mb-2">Response:</h3>
        <ResponseSection response={request.mainResponse} />
      </div>

      <div className="mb-6">
        <AlternativesSection
          alternatives={request.alternativeResponses}
          showAlternatives={showAlternatives}
          setShowAlternatives={setShowAlternatives}
        />
      </div>

      <NewAlternativeForm newAlternative={newAlternative} setNewAlternative={setNewAlternative} />
    </div>
  )
}
