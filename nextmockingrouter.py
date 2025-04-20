from fastapi import APIRouter, Path, HTTPException  # Import HTTPException
from pydantic import BaseModel, Field
from typing import List, Literal, Optional, Dict, Any  # Import Dict, Any, Optional
import uuid

# --- Define Data Structures ---

RequestStatus = Literal["complete", "partial", "none"]

class MockRequestSummary(BaseModel):
    id: str
    name: str
    question: str
    totalResponses: int
    annotatedResponses: int
    timestamp: str
    sftStatus: RequestStatus
    dpoStatus: RequestStatus

class Message(BaseModel):
    role: str
    content: str

class Annotation(BaseModel):
    reward: int
    by: str
    at: str

class ResponseDetail(BaseModel):
    id: str
    content: str
    model: str
    created: str
    annotations: List[Annotation]
    metadata: Optional[Dict[str, Any]] = None  # Use Dict for metadata
    is_json: bool
    obeys_schema: Optional[bool] = None

class RequestDetailData(BaseModel):
    id: str
    request_log_id: str
    intercept_key: str
    messages: List[Message]
    model: str
    response_format: Optional[Dict[str, Any]] = None  # Allow dict or null
    request_timestamp: str

class MockRequestDetail(BaseModel):
    id: str
    name: str
    pairNumber: int
    request: RequestDetailData
    mainResponse: ResponseDetail
    alternativeResponses: List[ResponseDetail]

# --- Mock Data ---

mock_requests_summary_data: List[MockRequestSummary] = [
    {
        "id": "f3ef3f5e-09c2-4a30-82a2-ecf4f460a1d9",
        "name": "What is 2+12?",
        "question": "What is 2+12?",
        "totalResponses": 10,
        "annotatedResponses": 8,
        "timestamp": "2025-04-19T11:22:44.054152Z",
        "sftStatus": "complete",
        "dpoStatus": "partial",
    },
    {
        "id": "a1b2c3d4-5e6f-7g8h-9i0j-klmno1p2q3r4",
        "name": "Explain quantum computing",
        "question": "Can you explain quantum computing in simple terms? I'm trying to understand how it differs from classical computing and why it's considered revolutionary...",
        "totalResponses": 15,
        "annotatedResponses": 12,
        "timestamp": "2025-04-18T15:30:22.123456Z",
        "sftStatus": "complete",
        "dpoStatus": "complete",
    },
    {
        "id": "5e6f7g8h-9i0j-klmn-o1p2-q3r4s5t6u7v8",
        "name": "Python code review",
        "question": "Can you review this Python function that calculates Fibonacci numbers? I think it's inefficient but I'm not sure how to optimize it.",
        "totalResponses": 8,
        "annotatedResponses": 5,
        "timestamp": "2025-04-17T09:45:11.987654Z",
        "sftStatus": "partial",
        "dpoStatus": "none",
    },
    {
        "id": "9i0jklmn-o1p2-q3r4-s5t6-u7v8w9x0y1z2",
        "name": "Summarize article",
        "question": "Please summarize this article about climate change and provide the key points that I should remember.",
        "totalResponses": 12,
        "annotatedResponses": 7,
        "timestamp": "2025-04-16T14:20:33.456789Z",
        "sftStatus": "none",
        "dpoStatus": "partial",
    },
    {
        "id": "q3r4s5t6-u7v8-w9x0-y1z2-a3b4c5d6e7f8",
        "name": "Translation request",
        "question": "Can you translate this paragraph from English to Spanish? I need it for my presentation tomorrow.",
        "totalResponses": 6,
        "annotatedResponses": 6,
        "timestamp": "2025-04-15T17:55:42.234567Z",
        "sftStatus": "partial",
        "dpoStatus": "complete",
    },
]

mock_requests_details_data: Dict[str, MockRequestDetail] = {
    "f3ef3f5e-09c2-4a30-82a2-ecf4f460a1d9": {
        "id": "f3ef3f5e-09c2-4a30-82a2-ecf4f460a1d9",
        "name": "What is 2+12?",
        "pairNumber": 2,
        "request": {
            "id": "f3ef3f5e-09c2-4a30-82a2-ecf4f460a1d9",
            "request_log_id": "d4d2a938-0e3f-46ba-8414-21d72ae8c807",
            "intercept_key": "sk-intercept-v1-JHteQu40BvrlnOD4onvz0LZIpzBNv8t4qwMDO0hL3hSzCGw2kyHw",
            "messages": [
                {
                    "role": "system",
                    "content": "You are a helpful assistant",
                },
                {
                    "role": "user",
                    "content": "What is 2+12?",
                },
            ],
            "model": "openai/gpt-4.1-nano",
            "response_format": None,
            "request_timestamp": "2025-04-19T11:22:44.054152Z",
        },
        "mainResponse": {
            "id": "gen-1745061763-51UoTnHd5YbhmM8TMKK",
            "content": "2 + 12 equals 14.",
            "model": "openai/gpt-4.1-nano",
            "created": "2025-04-19T14:22:43Z",
            "annotations": [
                {
                    "reward": 1,
                    "by": "guest-rater",
                    "at": "2025-04-19T14:25:30Z",
                },
            ],
            "metadata": {
                "completion_id": "f3ef3f5e-09c2-4a30-82a2-ecf4f460a1d9",
                "annotation_target_id": "3b550e5c-9fb0-419c-9739-8106fe0d019c",
                "provider": "OpenAI",
                "model": "openai/gpt-4.1-nano",
                "prompt_tokens": 14,
                "completion_tokens": 9,
                "total_tokens": 23,
                "choice_finish_reason": "stop",
                "choice_role": "assistant",
                "choice_content": "2 + 12 equals 14.",
            },
            "is_json": False,
            "obeys_schema": None,
        },
        "alternativeResponses": [
            {
                "id": "alt-1",
                "content": "sdfsad",
                "model": "openai/gpt-4.1-nano",
                "created": "2025-04-19T14:25:40Z",
                "annotations": [],
                "metadata": None,
                "is_json": False,
                "obeys_schema": None,
            },
            {
                "id": "alt-2",
                "content": '{\n  "results": 14\n}',
                "model": "openai/gpt-4.1-nano",
                "created": "2025-04-19T14:50:44Z",
                "annotations": [
                    {
                        "reward": 1,
                        "by": "guest-rater",
                        "at": "2025-04-19T14:50:48Z",
                    },
                    {
                        "reward": 1,
                        "by": "guest-rater",
                        "at": "2025-04-19T14:50:49Z",
                    },
                ],
                "metadata": None,
                "is_json": True,
                "obeys_schema": False,
            },
            {
                "id": "alt-3",
                "content": '{\n  "result": 14\n}',
                "model": "openai/gpt-4.1-nano",
                "created": "2025-04-19T14:50:44Z",
                "annotations": [
                    {
                        "reward": 1,
                        "by": "guest-rater",
                        "at": "2025-04-19T14:50:48Z",
                    },
                    {
                        "reward": 1,
                        "by": "guest-rater",
                        "at": "2025-04-19T14:50:49Z",
                    },
                ],
                "metadata": None,
                "is_json": True,
                "obeys_schema": True,
            },
        ],
    },
    "a1b2c3d4-5e6f-7g8h-9i0j-klmno1p2q3r4": {
        "id": "a1b2c3d4-5e6f-7g8h-9i0j-klmno1p2q3r4",
        "name": "Multi-turn conversation",
        "pairNumber": 3,
        "request": {
            "id": "a1b2c3d4-5e6f-7g8h-9i0j-klmno1p2q3r4",
            "request_log_id": "e5f6g7h8-i9j0-k1l2-m3n4-o5p6q7r8s9t0",
            "intercept_key": "sk-intercept-v1-KJteRu50CwsmoPE5pnwz1MZJqzCOw9u5rwNEP1iM4iTzDHx3lzIx",
            "messages": [
                {
                    "role": "system",
                    "content": "You are a helpful assistant",
                },
                {
                    "role": "user",
                    "content": "What is 2+12?",
                },
                {
                    "role": "assistant",
                    "content": "It is 14.",
                },
                {
                    "role": "user",
                    "content": "What is the double of that?",
                },
            ],
            "model": "openai/gpt-4.1-nano",
            "response_format": None,
            "request_timestamp": "2025-04-18T15:30:22.123456Z",
        },
        "mainResponse": {
            "id": "gen-1745061764-62VpUnIe6ZchnN9UNLM",
            "content": "The double of 14 is 28.",
            "model": "openai/gpt-4.1-nano",
            "created": "2025-04-18T15:30:25Z",
            "annotations": [],
            "metadata": {
                "completion_id": "a1b2c3d4-5e6f-7g8h-9i0j-klmno1p2q3r4",
                "annotation_target_id": "4c651f6d-0gc1-520d-0840-9217gf1e120d",
                "provider": "OpenAI",
                "model": "openai/gpt-4.1-nano",
                "prompt_tokens": 32,
                "completion_tokens": 7,
                "total_tokens": 39,
                "choice_finish_reason": "stop",
                "choice_role": "assistant",
                "choice_content": "The double of 14 is 28.",
            },
            "is_json": False,
            "obeys_schema": None,
        },
        "alternativeResponses": [],
    },
    "json-example-id": {
        "id": "json-example-id",
        "name": "JSON Response Example",
        "pairNumber": 4,
        "request": {
            "id": "json-example-id",
            "request_log_id": "json-log-id",
            "intercept_key": "sk-intercept-v1-json-example",
            "messages": [
                {
                    "role": "system",
                    "content": "You are a helpful assistant that responds in JSON format.",
                },
                {
                    "role": "user",
                    "content": "Give me information about the planet Mars in JSON format.",
                },
            ],
            "model": "openai/gpt-4.1-nano",
            "response_format": {"type": "json_object"},
            "request_timestamp": "2025-04-20T10:15:30.123456Z",
        },
        "mainResponse": {
            "id": "json-response-1",
            "content": '{\n  "planet": "Mars",\n  "diameter": "6,779 km",\n  "mass": "6.42 × 10^23 kg",\n  "gravity": "3.721 m/s²",\n  "day_length": "24.6 hours",\n  "year_length": "687 Earth days",\n  "moons": ["Phobos", "Deimos"],\n  "atmosphere": {\n    "composition": ["CO2", "Nitrogen", "Argon"],\n    "pressure": "0.006 atm"\n  }\n}',
            "model": "openai/gpt-4.1-nano",
            "created": "2025-04-20T10:15:35Z",
            "annotations": [
                {
                    "reward": 1,
                    "by": "json-validator",
                    "at": "2025-04-20T10:15:40Z",
                },
            ],
            "metadata": {
                "completion_id": "json-completion-id",
                "annotation_target_id": "json-target-id",
                "provider": "OpenAI",
                "model": "openai/gpt-4.1-nano",
                "prompt_tokens": 25,
                "completion_tokens": 18,
                "total_tokens": 43,
                "choice_finish_reason": "stop",
                "choice_role": "assistant",
                "choice_content": '{\n  "planet": "Mars",\n  "diameter": "6,779 km",\n  "mass": "6.42 × 10^23 kg",\n  "gravity": "3.721 m/s²",\n  "day_length": "24.6 hours",\n  "year_length": "687 Earth days",\n  "moons": ["Phobos", "Deimos"],\n  "atmosphere": {\n    "composition": ["CO2", "Nitrogen", "Argon"],\n    "pressure": "0.006 atm"\n  }\n}',
            },
            "is_json": True,
            "obeys_schema": True,
        },
        "alternativeResponses": [
            {
                "id": "json-alt-1",
                "content": '{\n  "name": "Mars",\n  "type": "Terrestrial planet",\n  "distance_from_sun": "227.9 million km",\n  "features": ["Red planet", "Olympus Mons", "Valles Marineris"]\n}',
                "model": "openai/gpt-4.1-nano",
                "created": "2025-04-20T10:16:00Z",
                "annotations": [],
                "metadata": None,
                "is_json": True,
                "obeys_schema": True,
            },
            {
                "id": "json-alt-2",
                "content": '{\n  "planet": "Mars",\n  "color": "Red",\n  "position": "Fourth planet from the Sun"\n}',
                "model": "openai/gpt-4.1-nano",
                "created": "2025-04-20T10:16:30Z",
                "annotations": [],
                "metadata": None,
                "is_json": True,
                "obeys_schema": False,
            },
        ],
    },
}

# --- Router ---

router = APIRouter(
    prefix="/mock-next",
    tags=["Mock Data for Next.js Frontend"],
)

@router.get("/{project_id}/requests-summary", response_model=List[MockRequestSummary])
async def get_mock_requests_summary(
    project_id: uuid.UUID = Path(..., description="The UUID of the project")
):
    print(f"Received summary request for project ID: {project_id}")
    return mock_requests_summary_data

@router.get("/{project_id}/requests/{request_id}", response_model=MockRequestDetail)
async def get_mock_request_details(
    project_id: uuid.UUID = Path(..., description="The UUID of the project"),
    request_id: str = Path(..., description="The ID of the request")
):
    """
    Returns mock details for a specific request ID.
    """
    print(f"Received detail request for project ID: {project_id}, Request ID: {request_id}")
    request_detail = mock_requests_details_data.get(request_id)
    if request_detail:
        return request_detail
    else:
        raise HTTPException(status_code=404, detail=f"Request with ID '{request_id}' not found.")