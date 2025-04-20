from fastapi import APIRouter, Path # Import Path
from pydantic import BaseModel
from typing import List, Literal
import uuid # Import uuid

# Define the status type matching the frontend
RequestStatus = Literal["complete", "partial", "none"]

# Define the Pydantic model matching the frontend's MockRequest interface
class MockRequestSummary(BaseModel):
    id: str
    name: str
    question: str
    totalResponses: int
    annotatedResponses: int
    timestamp: str # Keep as string for simplicity, FastAPI handles datetime conversion if needed later
    sftStatus: RequestStatus
    dpoStatus: RequestStatus

# Replicate the mock data from the frontend
mock_requests_data: List[MockRequestSummary] = [
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
    "question":
      "Can you explain quantum computing in simple terms? I'm trying to understand how it differs from classical computing and why it's considered revolutionary...",
    "totalResponses": 15,
    "annotatedResponses": 12,
    "timestamp": "2025-04-18T15:30:22.123456Z",
    "sftStatus": "complete",
    "dpoStatus": "complete",
  },
  {
    "id": "5e6f7g8h-9i0j-klmn-o1p2-q3r4s5t6u7v8",
    "name": "Python code review",
    "question":
      "Can you review this Python function that calculates Fibonacci numbers? I think it's inefficient but I'm not sure how to optimize it.",
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

# Create the router instance
router = APIRouter(
    prefix="/mock-next", # Optional prefix for all routes in this router
    tags=["Mock Data for Next.js Frontend"], # Tag for OpenAPI docs
)

# Modify the endpoint to include projectId
@router.get("/{project_id}/requests-summary", response_model=List[MockRequestSummary])
async def get_mock_requests_summary(
    project_id: uuid.UUID = Path(..., description="The UUID of the project") # Use Path for validation
):
    """
    Returns a list of mock request summaries for the overview table.
    (Currently ignores project_id and returns all mock data).
    """
    # TODO: Later, when fetching real data, use project_id to filter
    print(f"Received request for project ID: {project_id}") # Log that we got the ID
    return mock_requests_data

# You could add more endpoints here later for mock details, etc.
# For example:
# @router.get("/request-details/{request_id}")
# async def get_mock_request_details(request_id: str):
#     # Logic to find and return mock details for the given ID
#     pass